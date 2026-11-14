"use client"; // error boundaries are client components

// Catches errors from app/(app)/layout.tsx and the login page, e.g. when the API is not running.
export { default } from "@/components/error-view";
