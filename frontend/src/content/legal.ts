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

## Where it is stored

Account and course data is stored in Japan (Supabase, Tokyo). The application interface runs from Vercel in Japan, and the website files are delivered from servers close to you. Submitted code is checked on a private server in Sydney, Australia. This means your data can leave the country you live in.

## What your browser keeps

When you sign in, your browser keeps a sign-in session. While you work on a lab it may keep an unsent copy of your code on your device so nothing is lost if your connection drops. We use no advertising or tracking cookies. Signing out ends the session; clearing site data removes the local copy.

## Backups

Copies of the course database are made by the course team for recovery. They hold the same information as above and are kept for up to 4 weeks, then replaced.

## Age

The service is for learners enrolled in the course. If you are under the age where you may agree to this yourself, your school or guardian must allow you to use it.

## How long we keep it

- Account and learning record: while you are enrolled and for 12 months after, then deleted or made anonymous.
- Teacher notes: the same as the learning record.
- Security records: 12 months.
- Website and server logs: up to 30 days.

## Your choices

Ask ${CONTACT} to see your data, correct it, or delete it. Requests are handled by a person, not automatically, and deleting your account removes your learning record (backups are replaced within 4 weeks). You can also complain to the data-protection authority in your country.

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
