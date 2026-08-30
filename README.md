# 🍞 Breadcrumbs

A smart student productivity app that auto-schedules your to-do list around your life.

## What is Breadcrumbs?

Breadcrumbs connects to your Google Calendar, reads your existing commitments, and intelligently slots your tasks into available free time. You shouldn't have to think about *when* to do things, only *what* needs to get done.

The scheduling algorithm optimizes for three things:
- **Free time** - tasks are only scheduled into windows that actually exist in your calendar
- **Subject grouping** - similar subjects are batched together based on cognitive load research (e.g. math → math → history → history, not math → history → math)
- **Time estimation** - Breadcrumbs weighs your own estimate against historical data from similar past tasks to produce a more accurate prediction over time

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
- [ ] Canvas / Google Classroom integration

## Getting Started

> Setup instructions coming soon.

## Contributing

This project is currently in early development. Contributions are not yet open, but feel free to open issues for bugs or feature suggestions.

## License

MIT
