'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';

export function PatchesPage() {
  const [patches, setPatches] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchPatches();
  }, []);

  const fetchPatches = () => {
    fetch('/api/patches')
      .then(res => res.json())
      .then(data => setPatches(data));
  };

  const togglePatch = async (id: string, currentStatus: boolean) => {
    setLoading(true);
    try {
      const res = await fetch('/api/patches', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, enabled: !currentStatus })
      });

      if (res.ok) {
        toast.success(`Patch ${!currentStatus ? 'enabled' : 'disabled'} successfully`);
        fetchPatches(); // Refresh list
      } else {
        toast.error('Failed to update patch');
      }
    } catch (e) {
      toast.error('Error updating patch');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-3xl font-bold">Modular Patch Manager</h1>
      <p className="text-muted-foreground">Toggle gameplay features and economy systems.</p>

      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
        {patches.map((patch: any) => (
          <Card key={patch.id} className={patch.enabled ? "border-primary/50" : ""}>
            <CardHeader className="pb-2">
              <div className="flex justify-between items-start">
                <div>
                  <CardTitle className="text-lg">{patch.name}</CardTitle>
                  <CardDescription className="text-xs pt-1">{patch.file || 'System Patch'}</CardDescription>
                </div>
                <Switch
                  checked={patch.enabled}
                  onCheckedChange={() => togglePatch(patch.id, patch.enabled)}
                  disabled={loading}
                />
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col gap-4 text-sm text-muted-foreground min-h-[80px]">
                {patch.desc}
              </div>
              <div className="flex justify-between items-center pt-4 border-t mt-4">
                <Badge variant={patch.enabled ? "default" : "outline"}>
                  {patch.enabled ? "Active" : "Disabled"}
                </Badge>
                {!patch.fileExists && (
                  <Badge variant="destructive" className="text-[10px]">File Missing</Badge>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
export default PatchesPage;
