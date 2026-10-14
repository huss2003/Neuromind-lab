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


export const ACCEPTABLE_USE = `## Learning honestly

NeuroMind Lab only works if scores mean something. These rules apply to everyone who uses it.

- Do your own graded work. Ask your teacher before using help from other people or AI tools on a graded lab.
- Do not share, copy or look for hidden tests, answer keys or other learners' work.
- Do not try to break, overload, scan or bypass the site, the grader or its limits. Code you submit runs in a locked-down sandbox with no network; attempts to escape it, read the system or slow it for others are misuse.
- Do not put passwords, keys, personal data or anything illegal in code you submit.
- Use one account, your own.

## If you break these rules

A teacher or administrator may remove an attempt, pause an account or ask you to explain. Fair marking matters more than a single score. If you think a decision is wrong, tell ${CONTACT}.`;

export const RETENTION = `## How long information is kept

- **Account details:** while you are enrolled and for 12 months after, then deleted or made anonymous.
- **Progress, answers, lab attempts, submitted code and drafts:** the same.
- **Teacher notes about your work:** the same.
- **Security records** (sensitive actions, denied access): 12 months.
- **Website and server logs:** up to 30 days.
- **Recovery copies of the course database:** up to 4 weeks, then replaced.

## Deleting your information

Ask ${CONTACT}. A person handles the request, removes your account, and your learning record goes with it. Recovery copies disappear when they are replaced, within 4 weeks.

These periods are proposals by the course team. They are shown here so you know what to expect and may change; changes are announced on this page.`;

export const ACCESSIBILITY = `## Our aim

NeuroMind Lab should be usable with a keyboard, a screen reader, magnification and different devices. We aim for WCAG 2.1 level AA.

## What has been checked

- Automated checks of every main screen at desktop and phone widths.
- Keyboard-only use of sign-in, lessons, knowledge checks and the lab, with a skip-to-content link.
- Each page has its own title and a single main heading, and keyboard focus moves to the new page after you navigate.
- Quiz results and status messages are announced to screen readers.

## What has not been checked yet

- Testing with real screen readers (NVDA, JAWS, VoiceOver, TalkBack) by people who use them.
- Lecture videos: captions and transcripts are supported, but recordings are not published yet.
- The code editor is a third-party component. A plain text editor is available through "Use simple text editor".

## Tell us about a barrier

Contact ${CONTACT}. Say what you were doing, the device and any assistive technology. We will reply with a workaround or a fix date.`;

export const SECURITY = `## How we protect the service

- Sign-in is handled by Supabase Auth. Passwords are never visible to teachers or administrators.
- Every request is checked on the server: who you are, your role and whether the item belongs to you. The browser is never trusted for scores or completion.
- Official scores come only from the grader. Submitted code runs in an isolated container with no network, limited memory and time, and is thrown away afterwards.
- Hidden tests are never sent to your browser.
- Sensitive actions are recorded in a security log without your code or password.

## Reporting a problem

If you find a security problem, please do not test it further or share it. Tell ${CONTACT} what you saw and when. Reports made in good faith will not be treated as misuse.

## Honest limits

This is a small learning service. It has automated tests and load checks for a few dozen learners, but it has not had an independent security audit.`;
