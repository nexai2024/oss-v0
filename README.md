This is a [Next.js](https://nextjs.org/) project bootstrapped with [`create-next-app`](https://github.com/vercel/next.js/tree/canary/packages/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/basic-features/font-optimization) to automatically optimize and load Inter, a custom Google Font.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js/) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/deployment) for more details.

---

## Prompt Pilot Backend

This section pertains to the FastAPI backend for Prompt Pilot.

### Running with Docker (Backend)

To build and run the backend application using Docker Compose:

1.  Ensure you have Docker and Docker Compose installed.
2.  Navigate to the project root directory (where `Dockerfile` and `docker-compose.yml` are located).
3.  Build the Docker image for the backend:
    ```bash
    docker-compose build backend
    ```
    (If you only have the backend service in your `docker-compose.yml`, `docker-compose build` is also fine.)
4.  Run the backend application:
    ```bash
    docker-compose up backend
    ```
    (If you only have the backend service, `docker-compose up` is also fine.)

The backend API will be available at [http://localhost:8000](http://localhost:8000).
The UI pages served via Jinja2 by the backend will also be accessible (e.g., starting at [http://localhost:8000/view/login](http://localhost:8000/view/login)).

To run in detached mode:
```bash
docker-compose up -d backend
```

To stop the service:
```bash
docker-compose down
```
