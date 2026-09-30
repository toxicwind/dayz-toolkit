'use client';

import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface XmlSyntaxHighlighterProps {
    code: string;
    className?: string;
}

export function XmlSyntaxHighlighter({ code, className = '' }: XmlSyntaxHighlighterProps) {
    return (
        <SyntaxHighlighter
            language="xml"
            style={vscDarkPlus}
            customStyle={{
                margin: 0,
                padding: '1rem',
                background: 'transparent',
                fontSize: '0.875rem',
                lineHeight: '1.625',
            }}
            wrapLongLines
            showLineNumbers
            className={className}
        >
            {code}
        </SyntaxHighlighter>
    );
}
export default XmlSyntaxHighlighter;

export { XmlSyntaxHighlighter };
