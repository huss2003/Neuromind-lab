/** Plain-language privacy notice and terms of use. DRAFTS: the course owner must review them (ideally with legal advice) and fill in
 *  the operator name and contact before real learners use the service. */
export const OPERATOR = 'the NeuroMind Lab course team';
export const CONTACT = 'your teacher or course administrator';

export const PRIVACY = `## What this notice covers

NeuroMind Lab is a learning site. This page says what information it keeps about you, why, who can see it and how long it is kept. It is a draft that the course owner must review before real learners use the service.

## What we keep

- **Your account:** your email address, your name and your role (learner, teacher or administrator).
- **Your learning record:** which lessons you finished, your answers to knowledge checks, your lab attempts, scores and hints used, and the code you submit for grading.
- **Your drafts:** the code you are working on, saved so you can come back to it.
- **Teacher notes:** feedback your teacher writes about your work. Notes marked for you are shown to you.
- **Security records:** a log of sensitive actions such as sign-in problems, role changes and denied access. These records never contain your code or password.

## Why

To run the course, mark your work fairly, show you your progress, let your teacher help you, and keep the service safe.

## Who can see it

- You can see your own record.
- A teacher can see the record of learners assigned to them, including submitted code. A teacher cannot see other learners.
- Administrators can manage accounts and see security records.
- Hidden test answers are never shown to learners.

## Services that process your data

- **Supabase** stores accounts and course data.
- **Vercel** serves the website and the application interface.
- **Amazon Web Services** runs the grader that checks submitted code. The grader keeps nothing after it returns a result.
- **jsDelivr** delivers the code editor and the in-browser Python runtime, so your browser contacts it when you open a lab.

We do not sell your data and we do not use it for advertising.

## How long we keep it

- Account and learning record: while you are enrolled and for 12 months after, then deleted or made anonymous.
- Teacher notes: the same as the learning record.
- Security records: 12 months.
- Website and server logs: up to 30 days.

## Your choices

Ask ${CONTACT} to see your data, correct it, or delete it. Deleting your account removes your learning record.

## Please do not

Put passwords, keys or personal secrets in code you submit or in anything you type into the site.`;

export const TERMS = `## Using NeuroMind Lab

These are the basic rules for using the site. They are a draft that the course owner must review before real learners use the service.

## Your account

- Keep your password private and use your own account only.
- Tell ${CONTACT} if you think someone else used your account.

## Doing your own work

- Graded attempts must be your own work unless your teacher says otherwise.
- Do not share hidden tests, answers to other learners' work, or access to graded material.
- Do not try to break, overload or bypass the site, the grader or its limits. Code you submit runs in a restricted environment with no network access; attempts to escape it are treated as misuse.

## Fair marking

- You may try the lab as often as you like. Your best valid score is the one kept.
- If the grading system fails, the attempt is not marked against you.
- Scores are produced by the grader; teachers cannot change a score on this site.

## Availability

We aim to keep the service available but cannot promise it will never be interrupted. Your saved work is stored on our servers; copy important code somewhere safe too.

## Changes and contact

These terms may change. Questions go to ${CONTACT}.`;
