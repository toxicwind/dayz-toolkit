'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import { toast } from 'sonner';

export function ConfigPage() {
  const [files, setFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch('/api/files/json')
      .then(res => res.json())
      .then(data => setFiles(data));
  }, []);

  const loadFile = async (filename: string) => {
    setLoading(true);
    try {
      const res = await fetch(`/api/files/json?file=${filename}`);
      const data = await res.json();
      setFileContent(JSON.stringify(data.content, null, 4));
      setSelectedFile(filename);
    } catch (e) {
      toast.error('Failed to load file');
    } finally {
      setLoading(false);
    }
  };

  const saveFile = async () => {
    if (!selectedFile) return;
    try {
      // Validate JSON first
      let parsedContent;
      try {
        parsedContent = JSON.parse(fileContent);
      } catch (e) {
        toast.error('Invalid JSON syntax');
        return;
      }

      await fetch('/api/files/json', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file: selectedFile, content: parsedContent })
      });
      toast.success('Configuration saved successfully');
    } catch (e) {
      toast.error('Failed to save file');
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">JSON Configuration</h1>
        {selectedFile && (
          <Button onClick={saveFile} disabled={loading}>Save Changes</Button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 h-[calc(100vh-200px)]">
        <Card className="md:col-span-1">
          <CardHeader>
            <CardTitle>Configs</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <ScrollArea className="h-[700px] px-4">
              <div className="space-y-1 py-4">
                {files.map((file: string) => (
                  <Button
                    key={file}
                    variant={selectedFile === file ? "secondary" : "ghost"}
                    className="w-full justify-start text-xs truncate"
                    onClick={() => loadFile(file)}
                  >
                    {file}
                  </Button>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
        <Card className="md:col-span-3">
          <CardHeader>
            <CardTitle>{selectedFile || 'Editor'}</CardTitle>
          </CardHeader>
          <CardContent className="h-full">
            <Textarea
              value={fileContent}
              onChange={(e) => setFileContent(e.target.value)}
              className="h-[700px] font-mono text-xs whitespace-pre"
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
export default ConfigPage;
