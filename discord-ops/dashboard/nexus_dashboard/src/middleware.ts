import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

// Protect all routes under /dashboard
const isProtectedRoute = createRouteMatcher(['/dashboard(.*)']);

export default clerkMiddleware(async (auth, req) => {
    const { pathname, searchParams } = req.nextUrl;
    const timestamp = new Date().toISOString();

    // HYPER-VERBOSE TELEMETRY
    console.log(`[${timestamp}] 🚀 REQUEST: ${req.method} ${pathname}${searchParams ? '?' + searchParams : ''}`);

    if (isProtectedRoute(req)) {
        const { userId, redirectToSignIn } = await auth();

        console.log(`[${timestamp}] 🔐 AUTH-CHECK: path=${pathname} userId=${userId || 'GUEST'}`);

        if (!userId) {
            console.warn(`[${timestamp}] ⚠️ UNAUTHORIZED: Redirecting to Sign-In`);
            return redirectToSignIn();
        }

        // Admin Access Control
        const ADMIN_ID = 'user_37Nl8EHyPWT4Xce2S26OxKPw04h';
        const CLERK_CHRIS_ID = process.env.CLERK_CHRIS_ID;
        const ALLOWED_USERS = [ADMIN_ID, CLERK_CHRIS_ID].filter(Boolean);

        if (ALLOWED_USERS.length > 0 && !ALLOWED_USERS.includes(userId)) {
            console.error(`[${timestamp}] 🚫 FORBIDDEN: User ${userId} not in allowed list [${ALLOWED_USERS.join(', ')}]`);
            return new NextResponse('Unauthorized: Access Denied', { status: 403 });
        }

        console.log(`[${timestamp}] ✅ AUTHORIZED: User ${userId}`);
    }
});

export const config = {
    matcher: [
        // Skip Next.js internals and all static files, unless found in search params
        '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
        // Always run for API routes
        '/(api|trpc)(.*)',
    ],
};
