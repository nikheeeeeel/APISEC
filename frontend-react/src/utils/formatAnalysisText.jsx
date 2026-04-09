/** Renders markdown-ish AI analysis (bold + fenced code) like Version Monitor. */
export function formatAnalysisText(text) {
  if (!text) return null;
  const blocks = text.split('```');
  return blocks.map((block, index) => {
    if (index % 2 === 1) {
      const lines = block.split('\n');
      const code = lines.slice(1).join('\n');
      return (
        <pre
          key={index}
          className="bg-slate-900 p-3 rounded-md my-2 overflow-x-auto text-xs font-mono text-gray-300 border border-slate-800"
        >
          <code>{code}</code>
        </pre>
      );
    }
    const paragraphs = block.split('\n\n').filter((p) => p.trim());
    return (
      <div key={index} className="space-y-2 mt-2">
        {paragraphs.map((p, pIndex) => {
          const parts = p.split(/(\*\*.*?\*\*)/g);
          return (
            <p key={pIndex} className="text-sm text-gray-300 leading-relaxed">
              {parts.map((part, i) => {
                if (part.startsWith('**') && part.endsWith('**')) {
                  return (
                    <strong key={i} className="text-purple-300 font-semibold">
                      {part.slice(2, -2)}
                    </strong>
                  );
                }
                return part;
              })}
            </p>
          );
        })}
      </div>
    );
  });
}
