import React from 'react';

export default function SettingsPage() {
  return (
    <div className="p-6 space-y-4">
      <h1 className="text-2xl font-semibold">Settings</h1>
      <p className="text-sm text-gray-400">
        RCON tests are disabled in this console build. Use the FTP log ingest, A2S status, and Nitrado
        restart controls instead.
      </p>
    </div>
  );
}
