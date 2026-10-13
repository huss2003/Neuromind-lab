-- Lecture 9 demo: shuffle the second question's options (stable per learner) and leave the first fixed.
update public.mcq_questions set shuffle_options = true where id = '00000000-0000-4000-8000-0000000000a2';
