'use client';

import { XmlFileManager } from '@/components/xml-editor/xml-file-manager';

export function EconomyConfigPage() {
    return (
        <div className="h-full p-6">
            <XmlFileManager
                title="Economy Configuration"
                filter="economy"
            />
        </div>
    );
}
export default EconomyConfigPage;
