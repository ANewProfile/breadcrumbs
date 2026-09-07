# Breadcrumbs

A smart student productivity app that auto-schedules your to-do list around your life.

## What is Breadcrumbs?

Breadcrumbs connects to your Google Calendar, reads your existing commitments, and intelligently slots your tasks into available free time. You shouldn't have to think about *when* to do things, only *what* needs to get done.

The scheduling algorithm optimizes for three things:
- **Free time**: tasks are only scheduled into your free time, based on your Google Calendar events
- **Subject grouping**: tasks of the same subject are scheduled next to each other based on cognitive load research (e.g. math → math → history → history, not math → history → math → history)
- **Time estimation**: Breadcrumbs weighs your own estimate against historical data from tasks of the same subject to produce a custom prediction of how long a task will *actually* take you

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React / Next.js · Tailwind CSS · TypeScript |
| Backend | Python |
| Database | MongoDB |
| Calendar | Google Calendar API |

## Roadmap

- [ ] ML-based time prediction (once sufficient per-user historical data exists)
- [ ] Collaboration / shared tasks for group projects

## Getting Started

You can just build from source by running `git clone git@github.com:ANewProfile/breadcrumbs`. Run the backend with `venv/bin/uvicorn main:app --reload` from within `/backend`. Run the frontend with `npm run dev` from within `/frontend`.

## Contributing

This is a one-man project from a student, so there is currently no CONTRIBUTING.md file. If you would like to contribute, please open a PR with detailed descriptions.

## License

MIT
