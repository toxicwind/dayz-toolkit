'use client';

import { XmlFileManager } from '@/components/xml-editor/xml-file-manager';

export function EventsConfigPage() {
    return (
        <div className="h-full p-6">
            <XmlFileManager
                title="Events Configuration"
                filter="events"
            />
        </div>
    );
}
export default EventsConfigPage;
