from app import create_app, db
from app.models.models import Schedule, Student, Course, TimeSlot, CoursePreference
from collections import defaultdict
import time

app = create_app()
with app.app_context():
    print("=== COMPREHENSIVE TESTING REPORT FOR 500 STUDENTS ===\n")
    
    # 1. Overall Statistics
    total_students = Student.query.count()
    total_schedules = Schedule.query.filter_by(semester='Spring2024').count()
    students_with_schedules = db.session.query(Schedule.student_id).filter_by(semester='Spring2024').distinct().count()
    
    print(f"1. OVERALL STATISTICS")
    print(f"   Total Students: {total_students}")
    print(f"   Students Successfully Scheduled: {students_with_schedules} ({students_with_schedules/total_students*100:.1f}%)")
    print(f"   Total Course Enrollments: {total_schedules}")
    print(f"   Average Courses per Student: {total_schedules/students_with_schedules:.2f}\n")
    
    # 2. Conflict Analysis
    print(f"2. CONFLICT ANALYSIS")
    conflicts = 0
    conflict_examples = []
    
    students = db.session.query(Schedule.student_id).filter_by(semester='Spring2024').distinct().all()
    for (student_id,) in students:
        schedules = Schedule.query.filter_by(student_id=student_id, semester='Spring2024').all()
        
        has_conflict = False
        for i, s1 in enumerate(schedules):
            for s2 in schedules[i+1:]:
                ts1 = TimeSlot.query.get(s1.timeslot_id)
                ts2 = TimeSlot.query.get(s2.timeslot_id)
                
                if ts1.day == ts2.day and not (ts1.end_time <= ts2.start_time or ts2.end_time <= ts1.start_time):
                    has_conflict = True
                    if len(conflict_examples) < 3:
                        conflict_examples.append({
                            'student_id': student_id,
                            'course1': Course.query.get(s1.course_id).name,
                            'course2': Course.query.get(s2.course_id).name,
                            'time': f"Day {ts1.day}, {ts1.start_time}-{ts1.end_time}"
                        })
                    break
            if has_conflict:
                break
        
        if has_conflict:
            conflicts += 1
    
    print(f"   Students with Time Conflicts: {conflicts} ({conflicts/students_with_schedules*100:.1f}%)")
    print(f"   Conflict-Free Students: {students_with_schedules - conflicts} ({(students_with_schedules-conflicts)/students_with_schedules*100:.1f}%)")
    
    # 3. Satisfaction Analysis
    print(f"\n3. SATISFACTION ANALYSIS")
    satisfaction_by_priority = defaultdict(int)
    total_by_priority = defaultdict(int)
    
    for student in Student.query.all():
        prefs = CoursePreference.query.filter_by(student_id=student.id).all()
        scheduled_courses = set(s.course_id for s in Schedule.query.filter_by(student_id=student.id, semester='Spring2024').all())
        
        for pref in prefs:
            total_by_priority[pref.priority] += 1
            if pref.course_id in scheduled_courses:
                satisfaction_by_priority[pref.priority] += 1
    
    print("   Preference Satisfaction by Priority:")
    for priority in sorted(total_by_priority.keys()):
        met = satisfaction_by_priority[priority]
        total = total_by_priority[priority]
        print(f"     Priority {priority}: {met}/{total} ({met/total*100:.1f}%)")
    
    # 4. Course Load Distribution
    print(f"\n4. COURSE LOAD DISTRIBUTION")
    load_distribution = defaultdict(int)
    
    for student in Student.query.all():
        course_count = Schedule.query.filter_by(student_id=student.id, semester='Spring2024').count()
        load_distribution[course_count] += 1
    
    for load in sorted(load_distribution.keys()):
        count = load_distribution[load]
        print(f"   {load} courses: {count} students ({count/total_students*100:.1f}%)")
    
    # 5. Course Utilization
    print(f"\n5. COURSE UTILIZATION")
    for course in Course.query.all():
        enrollments = Schedule.query.filter_by(course_id=course.id, semester='Spring2024').count()
        utilization = enrollments / course.capacity * 100 if course.capacity > 0 else 0
        status = "FULL" if enrollments >= course.capacity else "Available"
        print(f"   {course.name}: {enrollments}/{course.capacity} ({utilization:.1f}%) - {status}")
    
    # 6. Performance Metrics
    print(f"\n6. PERFORMANCE METRICS")
    start = time.time()
    for i in range(100):
        Schedule.query.filter_by(student_id=i+1, semester='Spring2024').all()
    end = time.time()
    print(f"   Avg query time per student schedule: {(end-start)/100*1000:.2f}ms")
    
    print(f"\n7. EDGE CASES")
    no_courses = sum(1 for s in Student.query.all() if Schedule.query.filter_by(student_id=s.id, semester='Spring2024').count() == 0)
    max_courses = sum(1 for s in Student.query.all() if Schedule.query.filter_by(student_id=s.id, semester='Spring2024').count() == 5)
    print(f"   Students with NO courses: {no_courses}")
    print(f"   Students with MAX (5) courses: {max_courses}")
    
    print("\n=== END OF REPORT ===")
