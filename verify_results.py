from app import create_app, db
from app.models.models import Schedule, Student, Course, TimeSlot, CoursePreference
from collections import defaultdict
import random

app = create_app()
with app.app_context():
    print("=== COMPREHENSIVE VERIFICATION OF SCHEDULING RESULTS ===\n")
    
    # 1. VERIFY TIME CONFLICT DETECTION
    print("1. TIME CONFLICT VERIFICATION")
    real_conflicts = 0
    conflict_details = []
    
    all_students = Student.query.all()
    for student in all_students:
        schedules = Schedule.query.filter_by(student_id=student.id, semester='Spring2024').all()
        
        # Build a time map for this student
        time_map = defaultdict(list)
        for schedule in schedules:
            ts = TimeSlot.query.get(schedule.timeslot_id)
            course = Course.query.get(schedule.course_id)
            
            # Create time slots for each 30-minute interval
            current_time = ts.start_time
            while current_time < ts.end_time:
                time_key = (ts.day, current_time.hour, current_time.minute)
                time_map[time_key].append({
                    'course': course.name,
                    'room': ts.room,
                    'full_time': f"{ts.start_time}-{ts.end_time}"
                })
                # Move to next 30-minute slot
                if current_time.minute == 0:
                    current_time = current_time.replace(minute=30)
                else:
                    current_time = current_time.replace(hour=current_time.hour + 1, minute=0)
        
        # Check for conflicts
        has_conflict = False
        for time_key, courses in time_map.items():
            if len(courses) > 1:
                has_conflict = True
                if len(conflict_details) < 5:  # Only store first 5 examples
                    conflict_details.append({
                        'student': student.name,
                        'time': f"Day {time_key[0]}, {time_key[1]:02d}:{time_key[2]:02d}",
                        'courses': [c['course'] for c in courses]
                    })
                break
        
        if has_conflict:
            real_conflicts += 1
    
    print(f"   Students with actual time conflicts: {real_conflicts}")
    if conflict_details:
        print("   Conflict examples:")
        for detail in conflict_details:
            print(f"     - {detail['student']} has {detail['courses']} at {detail['time']}")
    else:
        print("   ✓ No time conflicts found - VERIFIED")
    
    # 2. VERIFY SATISFACTION CALCULATION
    print("\n2. SATISFACTION CALCULATION VERIFICATION")
    
    # Manual calculation of satisfaction
    total_prefs_by_priority = defaultdict(int)
    met_prefs_by_priority = defaultdict(int)
    
    # Sample some students for detailed analysis
    sample_students = random.sample(all_students, min(10, len(all_students)))
    
    for student in all_students:
        prefs = CoursePreference.query.filter_by(student_id=student.id).all()
        scheduled_courses = set(s.course_id for s in Schedule.query.filter_by(
            student_id=student.id, semester='Spring2024'
        ).all())
        
        for pref in prefs:
            total_prefs_by_priority[pref.priority] += 1
            if pref.course_id in scheduled_courses:
                met_prefs_by_priority[pref.priority] += 1
        
        # Detailed check for sample students
        if student in sample_students:
            pref_count = len(prefs)
            scheduled_count = len(scheduled_courses)
            matched = len([p for p in prefs if p.course_id in scheduled_courses])
            print(f"   Student {student.id}: {matched}/{pref_count} preferences met, {scheduled_count} courses scheduled")
    
    print("\n   Satisfaction by Priority (Manual Calculation):")
    for priority in sorted(total_prefs_by_priority.keys()):
        if total_prefs_by_priority[priority] > 0:
            rate = met_prefs_by_priority[priority] / total_prefs_by_priority[priority] * 100
            print(f"     Priority {priority}: {met_prefs_by_priority[priority]}/{total_prefs_by_priority[priority]} = {rate:.1f}%")
    
    # 3. VERIFY COURSE ASSIGNMENTS
    print("\n3. COURSE ASSIGNMENT VERIFICATION")
    
    # Check if students are assigned to courses they didn't prefer
    wrong_assignments = 0
    for schedule in Schedule.query.filter_by(semester='Spring2024').limit(100).all():
        pref = CoursePreference.query.filter_by(
            student_id=schedule.student_id,
            course_id=schedule.course_id
        ).first()
        if not pref:
            wrong_assignments += 1
    
    print(f"   Assignments without preferences: {wrong_assignments}")
    
    # 4. CAPACITY VERIFICATION
    print("\n4. CAPACITY CONSTRAINT VERIFICATION")
    
    capacity_violations = []
    for course in Course.query.all():
        enrollments = Schedule.query.filter_by(course_id=course.id, semester='Spring2024').count()
        if enrollments > course.capacity:
            capacity_violations.append({
                'course': course.name,
                'enrolled': enrollments,
                'capacity': course.capacity,
                'overflow': enrollments - course.capacity
            })
    
    if capacity_violations:
        print("   ⚠️  CAPACITY VIOLATIONS FOUND:")
        for v in capacity_violations:
            print(f"     - {v['course']}: {v['enrolled']}/{v['capacity']} (+{v['overflow']} overflow)")
    else:
        print("   ✓ All courses within capacity - VERIFIED")
    
    # 5. DISTRIBUTION ANALYSIS
    print("\n5. COURSE LOAD DISTRIBUTION ANALYSIS")
    
    load_dist = defaultdict(int)
    for student in all_students:
        count = Schedule.query.filter_by(student_id=student.id, semester='Spring2024').count()
        load_dist[count] += 1
    
    print("   Course load distribution:")
    for load in sorted(load_dist.keys()):
        print(f"     {load} courses: {load_dist[load]} students ({load_dist[load]/len(all_students)*100:.1f}%)")
    
    avg_load = sum(k*v for k,v in load_dist.items()) / len(all_students)
    print(f"   Average course load: {avg_load:.2f}")
    
    # 6. ALGORITHM BEHAVIOR VERIFICATION
    print("\n6. ALGORITHM BEHAVIOR ANALYSIS")
    
    # Check if the algorithm is just assigning first N preferences
    first_n_pattern = 0
    for student in random.sample(all_students, min(50, len(all_students))):
        prefs = CoursePreference.query.filter_by(student_id=student.id).order_by(
            CoursePreference.priority
        ).all()
        schedules = Schedule.query.filter_by(student_id=student.id, semester='Spring2024').all()
        
        if len(schedules) > 0 and len(prefs) >= len(schedules):
            # Check if scheduled courses match first N preferences exactly
            scheduled_course_ids = set(s.course_id for s in schedules)
            first_n_pref_ids = set(p.course_id for p in prefs[:len(schedules)])
            
            if scheduled_course_ids == first_n_pref_ids:
                first_n_pattern += 1
    
    print(f"   Students with exactly first N preferences: {first_n_pattern}/50 sampled")
    if first_n_pattern > 45:
        print("   ⚠️  Algorithm might be too simplistic - just assigning first N preferences")
    
    # 7. EDGE CASE VERIFICATION
    print("\n7. EDGE CASE ANALYSIS")
    
    # Students with unusual patterns
    no_first_choice = 0
    all_low_priority = 0
    
    for student in all_students:
        prefs = CoursePreference.query.filter_by(student_id=student.id).all()
        scheduled = set(s.course_id for s in Schedule.query.filter_by(
            student_id=student.id, semester='Spring2024'
        ).all())
        
        if prefs and scheduled:
            # Check if got first choice
            first_choice = next((p for p in prefs if p.priority == 1), None)
            if first_choice and first_choice.course_id not in scheduled:
                no_first_choice += 1
            
            # Check if only got low priority courses
            scheduled_priorities = [p.priority for p in prefs if p.course_id in scheduled]
            if scheduled_priorities and min(scheduled_priorities) >= 4:
                all_low_priority += 1
    
    print(f"   Students who didn't get their first choice: {no_first_choice}")
    print(f"   Students with only low-priority courses: {all_low_priority}")
    
    print("\n=== END OF VERIFICATION ===")
