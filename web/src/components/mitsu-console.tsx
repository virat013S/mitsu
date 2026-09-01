"use client";

import { Reactor } from "@/components/reactor";

type User = { id: number; display_name: string; gemini_configured: boolean };

export function MitsuConsole({ user, onSignOut }: { user: User; onSignOut: () => void }) {
  return (
    <div className="console-root">
      <Reactor state="idle" />
      <h1>MITSU</h1>
      <p>Welcome, {user.display_name}</p>
      <button onClick={onSignOut}>Sign Out</button>
    </div>
  );
}
