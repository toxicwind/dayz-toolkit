'use client';

import { XmlFileManager } from '@/components/xml-editor/xml-file-manager';

export function CfgConfigPage() {
    return (
        <div className="h-full p-6">
            <XmlFileManager
                title="General Configuration"
                filter={/^cfg/}
            />
        </div>
    );
}
export default CfgConfigPage;
