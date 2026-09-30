import { PatchManager } from '@/components/patches/PatchManager';
import PageContainer from '@/components/layout/page-container';

export const metadata = {
    title: 'Dashboard : Patch Management',
    description: 'Modular server feature toggles and mission patching engine'
};

export default function PatchesPage() {
    return (
        <PageContainer scrollable={true}>
            <div className="space-y-8 pb-12">
                <div className="flex flex-col gap-2">
                    <h2 className="text-4xl font-black tracking-tighter text-foreground uppercase italic flex items-center gap-4">
                        Patch <span className="text-primary">Management</span>
                    </h2>
                    <p className="text-muted-foreground text-sm font-mono uppercase tracking-widest bg-white/5 px-2 py-1 rounded inline-block w-fit">
                        Modular Server Feature Toggles & Hex Manipulation Engine
                    </p>
                </div>

                <PatchManager />
            </div>
        </PageContainer>
    );
}
