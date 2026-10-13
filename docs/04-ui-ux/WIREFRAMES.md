# Low-Fidelity Wireframes
These are text wireframes, not final mockups.

## Learner dashboard
```text
+------------------------------------------------------------------+
| NeuroMind Lab                                  Course | User      |
+-------------------+----------------------------------------------+
| Dashboard         | Welcome back                                 |
| My course         | [AI Foundations]                             |
| My progress       | Progress: 2 / 104 lectures                   |
|                   | [Resume Lecture 9]                           |
|                   | Continue learning: Lecture 9 [Resume]        |
+-------------------+----------------------------------------------+
```

## Lecture player
```text
+------------------------------------------------------------------+
| Course > Lecture 9                                                |
+-------------------------------+----------------------------------+
| VIDEO 16:9                    | Lesson outline                   |
|                               | [x] Intro                        |
|                               | [>] Theory 1                     |
|                               | [ ] MCQ 1                        |
|                               | [ ] Theory 2                     |
|                               | [ ] MCQ 2                        |
|                               | [ ] Practical                    |
+-------------------------------+----------------------------------+
| Objectives                 [Pause/Resume]             Progress 32%|
+------------------------------------------------------------------+
```

## MCQ overlay
```text
Video paused — Knowledge check 1
Which statement prints text in Python?
( ) echo("Hello")
( ) print("Hello")
( ) output("Hello")
( ) show("Hello")
                                      [Submit answer]
Result: Correct | Score 1/1 | Explanation...
                                      [Continue lesson]
```

## Coding lab
```text
Exercise: Print a variable
Instructions: Create student_name and print it.
+------------------------------+-----------------------------------+
| EDITOR                       | OUTPUT / RESULTS                  |
| student_name = "Aarav"        | Practice output: Aarav            |
| print(student_name)           | Official status: Not submitted    |
| [Run practice] [Submit grade] |                                   |
+------------------------------+-----------------------------------+
| Feedback / retry / submission history                               |
+------------------------------------------------------------------+
```

## Teacher editor
```text
Lecture details | Ordered segment editor
Title           | 1 Introduction [Video] [Edit] [Move]
Objectives      | 2 Theory 1 [Video] [Edit] [Move]
Status: Draft   | 3 MCQ 1 [Checkpoint] [Edit] [Move]
[Save draft]    | 4 Theory 2 [Video] ...
[Preview]       | 6 Practical [Video] 7 Exercise
[Validate]      | [Publish]
```

## Rules
Make current segment/next action obvious. Distinguish checkpoint, practice output and official grade. Provide keyboard-accessible fallback controls. Do not show green success until backend confirms.
