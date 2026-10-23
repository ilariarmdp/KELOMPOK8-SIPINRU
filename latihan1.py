class NotYetSetException(Exception):
    pass


# Class Student
class Student:
    def __init__(self):
        self.name = None

    def getName(self):
        return self.name

    def setName(self, n):
        self.name = n


# Class Assignment
class Assignment:
    def __init__(self):
        self.mark = -1

    def getMark(self):
        if self.mark == -1:
            raise NotYetSetException("Mark is not yet set")
        return self.mark

    def setMark(self, m):
        self.mark = m


# Class CourseRecord
class CourseRecord:
    def __init__(self):
        self.student = None
        self.assignments = []

    def getStudent(self):
        return self.student

    def setStudent(self, s):
        self.student = s

    def addAssignment(self, a):
        self.assignments.append(a)

    def getAssignments(self):
        return self.assignments


# Class Course
class Course:
    def __init__(self):
        self.title = None
        self.courseRecords = []

    def getTitle(self):
        return self.title

    def setTitle(self, t):
        self.title = t

    def addCourseRecord(self, cr):
        self.courseRecords.append(cr)

    def getCourseRecords(self):
        return self.courseRecords

    # Cetak seluruh mahasiswa yang mengambil course
    def printCourseStudents(self):
        for cr in self.courseRecords:
            student = cr.getStudent()
            if student is not None:
                print(student.getName())

    # Cetak mahasiswa dengan nilai rata-rata terbaik
    def printBestStudent(self):
        bestStudent = None
        bestAverage = -1

        for cr in self.courseRecords:
            student = cr.getStudent()
            assignments = cr.getAssignments()

            if student is None or not assignments:
                continue

            try:
                marks = [a.getMark() for a in assignments]
            except NotYetSetException:
                continue

            average = sum(marks) / len(marks)

            if average > bestAverage:
                bestAverage = average
                bestStudent = student

        if bestStudent is not None:
            print(
                bestStudent.getName(),
                "- Rata-rata:",
                bestAverage
            )
        else:
            print("Nilai mahasiswa belum tersedia.")

    # Cetak mahasiswa yang layak ujian akhir
    def printFinalExamStudents(self):
        for cr in self.courseRecords:
            student = cr.getStudent()
            assignments = cr.getAssignments()

            if student is None or not assignments:
                continue

            try:
                marks = [a.getMark() for a in assignments]
            except NotYetSetException:
                continue

            average = sum(marks) / len(marks)

            # Asumsi kriteria kelayakan: rata-rata minimal 50
            if average >= 50:
                print(
                    student.getName(),
                    "- Layak ujian akhir"
                )


# Program pengujian
if __name__ == "__main__":
    course = Course()
    course.setTitle("Pemrograman Berorientasi Objek")

    student = Student()
    student.setName("Andi")

    record = CourseRecord()
    record.setStudent(student)

    assignment1 = Assignment()
    assignment1.setMark(80)

    assignment2 = Assignment()
    assignment2.setMark(90)

    record.addAssignment(assignment1)
    record.addAssignment(assignment2)

    course.addCourseRecord(record)

    print("Mata kuliah:", course.getTitle())

    print("\nDaftar mahasiswa:")
    course.printCourseStudents()

    print("\nMahasiswa terbaik:")
    course.printBestStudent()

    print("\nMahasiswa layak ujian akhir:")
    course.printFinalExamStudents()

    # Pengujian exception
    assignment3 = Assignment()

    try:
        assignment3.getMark()
    except NotYetSetException as e:
        print("\nException:", e)
