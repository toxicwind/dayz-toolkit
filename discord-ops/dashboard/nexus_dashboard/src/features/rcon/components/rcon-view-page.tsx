import React from 'react';

export default function RconDisabledPage() {
  return (
    <div className="p-6 space-y-4">
      <h1 className="text-2xl font-semibold">RCON Disabled</h1>
      <p className="text-sm text-gray-400">
        This console-focused build no longer exposes a BattlEye RCON bridge. Use A2S, FTP logs, and
        Nitrado API tasks for observability and control.
      </p>
    </div>
  );
}
