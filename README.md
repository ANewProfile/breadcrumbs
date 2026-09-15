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

The website is available at [https://usebreadcrumbs.app](https://usebreadcrumbs.app). There is currently no CONTRIBUTING.md file, see the `Contributing` section below for help.

You can simply login with Google and start adding tasks! The app works best when you add consistent subject lines and time how long your tasks take either with the built-in timer or with your own system.

Enjoy!

## Contributing

This is a one-man project from a student, so there is currently no CONTRIBUTING.md file. If you would like to contribute, please open a PR with detailed descriptions. In addition, feel free to request features by opening Issues!

For development, you can clone the repo (`git clone git@github.com:ANewProfile/breadcrumbs`) and build from source. Run the backend with `venv/bin/uvicorn main:app --reload` from within `/backend`. Run the frontend with `npm run dev` from within `/frontend`. There is a built-in dev mode (which doesn't use the Google Calendar API and bypasses login) for running on localhost. Cloning to a local workspace will exclude important secrets and keys, so there will be no database or Google Login functionality.

## License

MIT
