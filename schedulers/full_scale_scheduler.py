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
        """Full-scale OR-Tools optimization for 500 students"""
        start_time = time.time()
        logger.info("Starting full-scale OR-Tools optimization for 500 students...")
        
        # Clear existing schedules
        Schedule.query.filter_by(semester=semester).delete()
        db.session.commit()
        
        # Initialize OR-Tools
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        
        # Get ALL students - full 500
        students = Student.query.all()
        courses = Course.query.all()
        timeslots = TimeSlot.query.all()
        
        logger.info(f"Optimizing for {len(students)} students, {len(courses)} courses, {len(timeslots)} timeslots")
        
        # Create realistic course sections
        # Large courses get multiple sections at different times
        course_sections = {}
        section_capacity = {}
        section_timeslots = {}
        
        section_id = 0
        for course in courses:
            course_sections[course.id] = []
            
            # Calculate number of sections based on demand
            demand = CoursePreference.query.filter_by(course_id=course.id).count()
            sections_needed = max(1, min(5, demand // 40))  # 40 students per section max
            
            capacity_per_section = course.capacity // sections_needed
            
            for i in range(sections_needed):
                section_id += 1
                course_sections[course.id].append(section_id)
                section_capacity[section_id] = capacity_per_section
                # Assign different timeslots to different sections
                section_timeslots[section_id] = timeslots[(course.id + i * 7) % len(timeslots)]
        
        logger.info(f"Created {section_id} course sections")
        
        # DECISION VARIABLES
        # x[s,sec] = 1 if student s is assigned to section sec
        x = {}
        for s in students:
            for c_id, sections in course_sections.items():
                for sec in sections:
                    var_name = f'x[{s.id},{sec}]'
                    x[s.id, sec] = self.model.NewBoolVar(var_name)
        
        # Helper: map section to course
        section_to_course = {}
        for c_id, sections in course_sections.items():
            for sec in sections:
                section_to_course[sec] = c_id
        
        # CONSTRAINTS
        
        # 1. Student takes at most one section of each course
        for s in students:
            for c_id, sections in course_sections.items():
                self.model.Add(
                    sum(x[s.id, sec] for sec in sections) <= 1
                )
        
        # 2. Time conflict constraints
        logger.info("Adding time conflict constraints...")
        for s in students:
            # Group sections by time
            time_groups = defaultdict(list)
            for sec, ts in section_timeslots.items():
                time_key = (ts.day, ts.start_time, ts.end_time)
                time_groups[time_key].append(sec)
            
            # Student can take at most one section at each time
            for time_key, sections in time_groups.items():
                if len(sections) > 1:
                    self.model.Add(
                        sum(x.get((s.id, sec), 0) for sec in sections) <= 1
                    )
        
        # 3. Section capacity constraints
        logger.info("Adding capacity constraints...")
        for sec, capacity in section_capacity.items():
            self.model.Add(
                sum(x.get((s.id, sec), 0) for s in students) <= capacity
            )
        
        # 4. Student course load constraints (3-5 courses)
        logger.info("Adding course load constraints...")
        for s in students:
            total_courses = sum(x.get((s.id, sec), 0) for sec in section_capacity.keys())
            self.model.Add(total_courses >= 3)
            self.model.Add(total_courses <= 5)
        
        # 5. Prerequisite constraints (example: CS201 requires CS101)
        cs101 = next((c for c in courses if c.course_code == 'CS101'), None)
        cs201 = next((c for c in courses if c.course_code == 'CS201'), None)
        
        if cs101 and cs201:
            for s in students:
                # If taking CS201, must also take CS101
                for sec201 in course_sections[cs201.id]:
                    self.model.Add(
                        x.get((s.id, sec201), 0) <= 
                        sum(x.get((s.id, sec101), 0) for sec101 in course_sections[cs101.id])
                    )
        
        # OBJECTIVE FUNCTION
        logger.info("Setting up objective function...")
        objective_terms = []
        
        # Get all preferences
        pref_lookup = defaultdict(dict)
        for pref in CoursePreference.query.all():
            pref_lookup[pref.student_id][pref.course_id] = pref.priority
        
        # Build objective
        for s in students:
            for sec, course_id in section_to_course.items():
                if course_id in pref_lookup[s.id]:
                    priority = pref_lookup[s.id][course_id]
                    # Weighted by priority: 1st=10, 2nd=6, 3rd=3, 4th=1, 5th=0
                    weight = max(0, 11 - 2 * priority)
                    objective_terms.append(weight * x.get((s.id, sec), 0))
                else:
                    # Small penalty for non-preferred courses
                    objective_terms.append(-2 * x.get((s.id, sec), 0))
        
        self.model.Maximize(sum(objective_terms))
        
        # SOLVE
        logger.info("Solving optimization problem...")
        
        # Set solver parameters for large problem
        self.solver.parameters.max_time_in_seconds = 60.0  # Allow more time for 500 students
        self.solver.parameters.num_search_workers = 4
        self.solver.parameters.log_search_progress = True
        
        # Add solution callback
        solution_printer = SolutionPrinter(students, section_to_course, x, len(students))
        status = self.solver.Solve(self.model, solution_printer)
        
        solve_time = time.time() - start_time
        
        # EXTRACT SOLUTION
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            logger.info(f"Solution found! Status: {self.solver.StatusName(status)}")
            
            schedules = []
            stats = defaultdict(int)
            
            for s in students:
                student_sections = []
                for sec in section_capacity.keys():
                    if (s.id, sec) in x and self.solver.Value(x[s.id, sec]) == 1:
                        student_sections.append(sec)
                        course_id = section_to_course[sec]
                        
                        schedule = Schedule(
                            student_id=s.id,
                            course_id=course_id,
                            timeslot_id=section_timeslots[sec].id,
                            semester=semester
                        )
                        schedules.append(schedule)
                        
                        # Track statistics
                        if course_id in pref_lookup[s.id]:
                            priority = pref_lookup[s.id][course_id]
                            stats[f'priority_{priority}'] += 1
                        else:
                            stats['unpreferred'] += 1
                
                stats[f'load_{len(student_sections)}'] += 1
            
            # Save schedules in batches
            if schedules:
                for i in range(0, len(schedules), 1000):
                    batch = schedules[i:i+1000]
                    db.session.bulk_save_objects(batch)
                    db.session.commit()
            
            # Store detailed statistics
            self.solution_stats = {
                'status': self.solver.StatusName(status),
                'objective_value': self.solver.ObjectiveValue(),
                'solve_time': solve_time,
                'num_conflicts': self.solver.NumConflicts(),
                'num_branches': self.solver.NumBranches(),
                'wall_time': self.solver.WallTime(),
                'assignments_made': len(schedules),
                'students_processed': len(students),
                'distribution': dict(stats),
                'solution_count': solution_printer.solution_count
            }
            
            logger.info(f"Optimization complete: {len(schedules)} assignments in {solve_time:.2f}s")
            return schedules
            
        else:
            logger.error(f"No solution found. Status: {self.solver.StatusName(status)}")
            self.solution_stats = {
                'status': self.solver.StatusName(status),
                'solve_time': solve_time,
                'error': 'No feasible solution found'
            }
            return []
    
    def calculate_metrics(self, semester):
        """Comprehensive metrics for 500 students"""
        schedules = Schedule.query.filter_by(semester=semester).all()
        all_students = Student.query.all()
        
        if not schedules:
            return {'error': 'No schedules found'}
        
        # Initialize metrics
        metrics = defaultdict(lambda: defaultdict(int))
        
        # Process each student
        for student in all_students:
            student_schedules = [s for s in schedules if s.student_id == student.id]
            prefs = CoursePreference.query.filter_by(student_id=student.id).all()
            pref_map = {p.course_id: p.priority for p in prefs}
            
            # Course load
            course_count = len(student_schedules)
            metrics['course_load'][course_count] += 1
            
            # Satisfaction analysis
            for sched in student_schedules:
                if sched.course_id in pref_map:
                    priority = pref_map[sched.course_id]
                    metrics['satisfaction'][f'priority_{priority}'] += 1
                else:
                    metrics['satisfaction']['unpreferred'] += 1
            
            # Check if got first choice
            if prefs and student_schedules:
                first_choices = [p.course_id for p in prefs if p.priority == 1]
                got_first = any(s.course_id in first_choices for s in student_schedules)
                metrics['first_choice']['got_first' if got_first else 'no_first'] += 1
            
            # Time utilization
            for sched in student_schedules:
                ts = TimeSlot.query.get(sched.timeslot_id)
                day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
                day = day_names[ts.day] if ts.day < 5 else f'Day{ts.day}'
                time_slot = f"{day} {ts.start_time}"
                metrics['time_distribution'][time_slot] += 1
        
        # Calculate conflict rate
        conflicts = 0
        for student in all_students:
            student_times = defaultdict(list)
            for s in [s for s in schedules if s.student_id == student.id]:
                ts = TimeSlot.query.get(s.timeslot_id)
                student_times[(ts.day, ts.start_time)].append(s)
            
            for times, scheds in student_times.items():
                if len(scheds) > 1:
                    conflicts += 1
                    break
        
        # Course utilization
        course_stats = {}
        for course in Course.query.all():
            enrolled = len([s for s in schedules if s.course_id == course.id])
            demand = CoursePreference.query.filter_by(course_id=course.id).count()
            course_stats[course.name] = {
                'enrolled': enrolled,
                'capacity': course.capacity,
                'demand': demand,
                'utilization': round(enrolled / course.capacity * 100, 1),
                'demand_ratio': round(demand / course.capacity, 2)
            }
        
        # Compile final metrics
        total_students = len(all_students)
        students_scheduled = len(set(s.student_id for s in schedules))
        
        # Satisfaction rates by priority
        total_by_priority = defaultdict(int)
        for pref in CoursePreference.query.all():
            total_by_priority[pref.priority] += 1
        
        satisfaction_rates = {}
        for priority in range(1, 6):
            satisfied = metrics['satisfaction'].get(f'priority_{priority}', 0)
            total = total_by_priority.get(priority, 0)
            if total > 0:
                satisfaction_rates[f'priority_{priority}'] = {
                    'satisfied': satisfied,
                    'total': total,
                    'rate': round(satisfied / total * 100, 1)
                }
        
        return {
            'summary': {
                'total_students': total_students,
                'students_scheduled': students_scheduled,
                'total_assignments': len(schedules),
                'avg_courses_per_student': round(len(schedules) / students_scheduled, 2) if students_scheduled else 0,
                'schedule_rate': round(students_scheduled / total_students * 100, 1)
            },
            'solver_performance': self.solution_stats,
            'course_load_distribution': dict(metrics['course_load']),
            'satisfaction_analysis': {
                'by_priority': satisfaction_rates,
                'first_choice_success': dict(metrics['first_choice']),
                'unpreferred_assignments': metrics['satisfaction'].get('unpreferred', 0)
            },
            'conflict_analysis': {
                'students_with_conflicts': conflicts,
                'conflict_rate': round(conflicts / students_scheduled * 100, 1) if students_scheduled else 0
            },
            'course_statistics': course_stats,
            'time_distribution': dict(sorted(metrics['time_distribution'].items(), 
                                           key=lambda x: x[1], reverse=True)[:10])
        }


class SolutionPrinter(cp_model.CpSolverSolutionCallback):
    """Progress callback for large optimization"""
    
    def __init__(self, students, section_to_course, x, total_students):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.students = students
        self.section_to_course = section_to_course
        self.x = x
        self.solution_count = 0
        self.start_time = time.time()
        self.total_students = total_students
        
    def on_solution_callback(self):
        self.solution_count += 1
        current_time = time.time() - self.start_time
        
        if self.solution_count % 5 == 0:
            assignments = sum(1 for key, var in self.x.items() if self.Value(var) == 1)
            logger.info(f'Solution {self.solution_count} at {current_time:.1f}s: '
                       f'{assignments} assignments, objective: {self.ObjectiveValue()}')
