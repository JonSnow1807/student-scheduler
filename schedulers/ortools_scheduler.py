from ortools.sat.python import cp_model
from app.models.models import Student, Course, TimeSlot, CoursePreference, Schedule
from app import db
import logging
import time
from collections import defaultdict

logger = logging.getLogger(__name__)

class SchedulerService:
    def __init__(self):
        self.model = None
        self.solver = None
        self.solution_stats = {}
        
    def optimize_schedules(self, semester):
        """Real OR-Tools constraint optimization"""
        start_time = time.time()
        logger.info("Starting OR-Tools constraint optimization...")
        
        # Clear existing schedules
        Schedule.query.filter_by(semester=semester).delete()
        db.session.commit()
        
        # Initialize OR-Tools
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        
        # Get data - limit for performance
        students = Student.query.limit(200).all()  # Start with 200 for reasonable solve time
        courses = Course.query.all()
        timeslots = TimeSlot.query.all()
        
        logger.info(f"Optimizing for {len(students)} students, {len(courses)} courses, {len(timeslots)} timeslots")
        
        # Create time conflict groups (timeslots that overlap)
        time_conflicts = self._find_time_conflicts(timeslots)
        
        # Assign courses to specific timeslots (one timeslot per course for simplicity)
        course_timeslots = {}
        for i, course in enumerate(courses):
            course_timeslots[course.id] = timeslots[i % len(timeslots)]
        
        # DECISION VARIABLES
        # x[s,c] = 1 if student s is assigned to course c
        x = {}
        for s in students:
            for c in courses:
                var_name = f'x[{s.id},{c.id}]'
                x[s.id, c.id] = self.model.NewBoolVar(var_name)
        
        # CONSTRAINTS
        
        # 1. Time conflict constraints - student cannot take conflicting courses
        logger.info("Adding time conflict constraints...")
        for s in students:
            for ts_group in time_conflicts:
                # Get courses scheduled at conflicting times
                conflicting_courses = [c for c in courses 
                                     if course_timeslots[c.id].id in ts_group]
                
                # Student can take at most one course from conflicting set
                if len(conflicting_courses) > 1:
                    self.model.Add(
                        sum(x[s.id, c.id] for c in conflicting_courses) <= 1
                    )
        
        # 2. Course capacity constraints
        logger.info("Adding capacity constraints...")
        for c in courses:
            self.model.Add(
                sum(x[s.id, c.id] for s in students) <= c.capacity
            )
        
        # 3. Student course load constraints (3-5 courses per student)
        logger.info("Adding course load constraints...")
        for s in students:
            total_courses = sum(x[s.id, c.id] for c in courses)
            self.model.Add(total_courses >= 3)
            self.model.Add(total_courses <= 5)
        
        # 4. Prerequisite constraints (if any) - example
        # If CS201 requires CS101, student must have taken CS101
        # (In a real system, you'd model this properly)
        
        # OBJECTIVE FUNCTION - Maximize weighted satisfaction
        logger.info("Setting up objective function...")
        objective_terms = []
        
        # Get all preferences
        all_preferences = CoursePreference.query.filter(
            CoursePreference.student_id.in_([s.id for s in students])
        ).all()
        
        # Create preference lookup
        pref_lookup = defaultdict(dict)
        for pref in all_preferences:
            pref_lookup[pref.student_id][pref.course_id] = pref.priority
        
        # Build objective: maximize sum of (weight * assignment)
        for s in students:
            for c in courses:
                if c.id in pref_lookup[s.id]:
                    priority = pref_lookup[s.id][c.id]
                    # Higher weight for higher priority (1st priority gets weight 5, 5th gets 1)
                    weight = 6 - priority
                    objective_terms.append(weight * x[s.id, c.id])
                else:
                    # Small penalty for courses not in preferences
                    objective_terms.append(-1 * x[s.id, c.id])
        
        self.model.Maximize(sum(objective_terms))
        
        # SOLVE
        logger.info("Solving optimization problem...")
        
        # Set solver parameters
        self.solver.parameters.max_time_in_seconds = 30.0
        self.solver.parameters.num_search_workers = 4
        
        # Add solution callback to track progress
        solution_printer = SolutionPrinter(students, courses, x)
        status = self.solver.Solve(self.model, solution_printer)
        
        solve_time = time.time() - start_time
        
        # EXTRACT SOLUTION
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            logger.info(f"Solution found! Status: {self.solver.StatusName(status)}")
            
            schedules = []
            assignments_made = 0
            
            for s in students:
                for c in courses:
                    if self.solver.Value(x[s.id, c.id]) == 1:
                        assignments_made += 1
                        schedule = Schedule(
                            student_id=s.id,
                            course_id=c.id,
                            timeslot_id=course_timeslots[c.id].id,
                            semester=semester
                        )
                        schedules.append(schedule)
            
            # Save schedules
            if schedules:
                db.session.bulk_save_objects(schedules)
                db.session.commit()
            
            # Store solution statistics
            self.solution_stats = {
                'status': self.solver.StatusName(status),
                'objective_value': self.solver.ObjectiveValue(),
                'solve_time': solve_time,
                'num_conflicts': self.solver.NumConflicts(),
                'num_branches': self.solver.NumBranches(),
                'wall_time': self.solver.WallTime(),
                'assignments_made': assignments_made,
                'solution_count': solution_printer.solution_count
            }
            
            logger.info(f"Optimization complete: {assignments_made} assignments in {solve_time:.2f}s")
            return schedules
            
        else:
            logger.error(f"No solution found. Status: {self.solver.StatusName(status)}")
            self.solution_stats = {
                'status': self.solver.StatusName(status),
                'solve_time': solve_time,
                'error': 'No feasible solution found'
            }
            return []
    
    def _find_time_conflicts(self, timeslots):
        """Find groups of timeslots that conflict (same day/time)"""
        conflicts = []
        processed = set()
        
        for i, ts1 in enumerate(timeslots):
            if i in processed:
                continue
                
            conflict_group = [ts1.id]
            processed.add(i)
            
            for j, ts2 in enumerate(timeslots[i+1:], i+1):
                if j in processed:
                    continue
                    
                # Check if timeslots conflict (same day and overlapping times)
                if ts1.day == ts2.day:
                    # Check time overlap
                    if not (ts1.end_time <= ts2.start_time or ts2.end_time <= ts1.start_time):
                        conflict_group.append(ts2.id)
                        processed.add(j)
            
            if len(conflict_group) > 1:
                conflicts.append(conflict_group)
        
        return conflicts
    
    def calculate_metrics(self, semester):
        """Calculate comprehensive metrics from OR-Tools solution"""
        schedules = Schedule.query.filter_by(semester=semester).all()
        all_students = Student.query.limit(200).all()  # Match optimization limit
        
        if not schedules:
            return {'error': 'No schedules found'}
        
        # Basic counts
        students_scheduled = set(s.student_id for s in schedules)
        
        # Satisfaction analysis
        satisfaction_by_priority = defaultdict(int)
        total_by_priority = defaultdict(int)
        preference_distances = []
        
        for student in all_students:
            student_schedules = [s for s in schedules if s.student_id == student.id]
            prefs = CoursePreference.query.filter_by(student_id=student.id).all()
            
            # Create preference ranking
            pref_ranking = {p.course_id: p.priority for p in prefs}
            
            for pref in prefs:
                total_by_priority[pref.priority] += 1
                
                # Check if this preference was satisfied
                if any(s.course_id == pref.course_id for s in student_schedules):
                    satisfaction_by_priority[pref.priority] += 1
            
            # Calculate average preference distance for this student
            if student_schedules and prefs:
                distances = []
                for sched in student_schedules:
                    if sched.course_id in pref_ranking:
                        distances.append(pref_ranking[sched.course_id])
                    else:
                        distances.append(6)  # Penalty for non-preferred course
                
                if distances:
                    preference_distances.append(sum(distances) / len(distances))
        
        # Time conflict verification
        conflicts = 0
        for student_id in students_scheduled:
            student_schedules = [s for s in schedules if s.student_id == student_id]
            
            # Check for time conflicts
            for i in range(len(student_schedules)):
                for j in range(i+1, len(student_schedules)):
                    ts1 = TimeSlot.query.get(student_schedules[i].timeslot_id)
                    ts2 = TimeSlot.query.get(student_schedules[j].timeslot_id)
                    
                    if ts1.day == ts2.day:
                        if not (ts1.end_time <= ts2.start_time or ts2.end_time <= ts1.start_time):
                            conflicts += 1
                            break
        
        # Course utilization
        course_util = {}
        for course in Course.query.all():
            enrolled = len([s for s in schedules if s.course_id == course.id])
            course_util[course.name] = {
                'enrolled': enrolled,
                'capacity': course.capacity,
                'utilization': round(enrolled / course.capacity * 100, 1)
            }
        
        # Calculate metrics
        metrics = {
            'optimization_stats': self.solution_stats,
            'coverage': {
                'total_students': len(all_students),
                'students_scheduled': len(students_scheduled),
                'coverage_rate': round(len(students_scheduled) / len(all_students) * 100, 1)
            },
            'assignments': {
                'total_schedules': len(schedules),
                'avg_courses_per_student': round(len(schedules) / len(students_scheduled), 2) if students_scheduled else 0
            },
            'satisfaction': {
                'by_priority': {
                    f'priority_{p}': {
                        'satisfied': satisfaction_by_priority[p],
                        'total': total_by_priority[p],
                        'rate': round(satisfaction_by_priority[p] / total_by_priority[p] * 100, 1) if total_by_priority[p] > 0 else 0
                    }
                    for p in range(1, 6) if total_by_priority[p] > 0
                },
                'avg_preference_distance': round(sum(preference_distances) / len(preference_distances), 2) if preference_distances else 0
            },
            'conflicts': {
                'time_conflicts': conflicts,
                'conflict_rate': round(conflicts / len(students_scheduled) * 100, 1) if students_scheduled else 0
            },
            'course_utilization': course_util,
            'algorithm_performance': {
                'solver_status': self.solution_stats.get('status', 'Unknown'),
                'objective_value': self.solution_stats.get('objective_value', 0),
                'solve_time_seconds': round(self.solution_stats.get('solve_time', 0), 2),
                'solution_count': self.solution_stats.get('solution_count', 0)
            }
        }
        
        return metrics


class SolutionPrinter(cp_model.CpSolverSolutionCallback):
    """Callback to print intermediate solutions during solving"""
    
    def __init__(self, students, courses, x):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.students = students
        self.courses = courses
        self.x = x
        self.solution_count = 0
        self.start_time = time.time()
        
    def on_solution_callback(self):
        self.solution_count += 1
        current_time = time.time() - self.start_time
        
        if self.solution_count % 10 == 0:  # Print every 10th solution
            logger.info(f'Solution {self.solution_count} found at {current_time:.2f}s, objective: {self.ObjectiveValue()}')
