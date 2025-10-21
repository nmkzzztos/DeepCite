import React, { useState, useEffect, useMemo, useCallback } from 'react';
import './Python.css';
import { debounce } from 'lodash';

interface PythonProps {
    code: string;
    withInput?: boolean;
    defaultInput?: string;
}

const PYTHON_KEYWORDS = [
    'def', 'class', 'if', 'else', 'elif', 'for', 'while', 'try',
    'except', 'finally', 'with', 'as', 'import', 'from', 'return',
    'raise', 'break', 'continue', 'pass', 'None', 'True', 'False'
];

const PYTHON_BUILTINS = [
    'print', 'len', 'range', 'int', 'str', 'float', 'list',
    'dict', 'set', 'tuple', 'input', 'sum', 'min', 'max'
];

const highlightPythonSyntax = (code: string): string => {
    // HTML encode function to safely encode HTML entities
    const htmlEncode = (str: string): string => {
        return str.replace(/&/g, '&amp;')
                  .replace(/</g, '&lt;')
                  .replace(/>/g, '&gt;')
                  .replace(/"/g, '&quot;')
                  .replace(/'/g, '&#39;');
    };

    const tokens = code.split(/(\s+|[.,(){}[\]=+\-*/<>!:]+)/).filter(Boolean);

    return tokens.map(token => {
        if (PYTHON_KEYWORDS.includes(token)) {
            return `<span class="keyword">${htmlEncode(token)}</span>`;
        }

        if (PYTHON_BUILTINS.includes(token)) {
            return `<span class="builtin">${htmlEncode(token)}</span>`;
        }

        if (token.startsWith('"') || token.startsWith("'")) {
            return `<span class="string">${htmlEncode(token)}</span>`;
        }

        if (/^\d+(\.\d+)?$/.test(token)) {
            return `<span class="number">${htmlEncode(token)}</span>`;
        }

        if (token.startsWith('#')) {
            return `<span class="comment">${htmlEncode(token)}</span>`;
        }

        if (/^[+\-*/<>=!&|^~]+$/.test(token)) {
            return `<span class="operator">${htmlEncode(token)}</span>`;
        }

        if (/^[a-zA-Z_]\w*(?=\s*\()/.test(token)) {
            return `<span class="function">${htmlEncode(token)}</span>`;
        }

        if (/^[A-Z][a-zA-Z0-9_]*$/.test(token)) {
            return `<span class="class">${htmlEncode(token)}</span>`;
        }

        return htmlEncode(token);
    }).join('');
};

export const Python: React.FC<PythonProps> = ({ 
    code, 
    withInput = false, 
    defaultInput = '' 
}) => {
    const [isExpanded, setIsExpanded] = useState(false);
    const [output, setOutput] = useState('');
    const [error, setError] = useState('');
    const [input, setInput] = useState(defaultInput);
    const [currentCode, setCurrentCode] = useState(code);

    const expandIcon = (
        <svg className='code-control-icon' fill="#000000" viewBox="0 -2 20 20" xmlns="http://www.w3.org/2000/svg">
            <path d="M12.7361611,0.063952038 C13.2551391,0.263360331 13.5227261,0.869148905 13.3338336,1.41701869 L8.54555162,15.3051026 C8.35665911,15.8529724 7.78281676,16.1354563 7.26383885,15.936048 C6.74486095,15.7366397 6.47727387,15.1308511 6.66616638,14.5829813 L11.4544484,0.694897379 C11.6433409,0.147027596 12.2171832,-0.135456255 12.7361611,0.063952038 Z M2.41421356,8.25614867 L5.94974747,11.9885083 C6.34027176,12.4007734 6.34027176,13.0691871 5.94974747,13.4814522 C5.55922318,13.8937173 4.9260582,13.8937173 4.53553391,13.4814522 L0.292893219,9.0026206 C-0.0976310729,8.59035554 -0.0976310729,7.9219418 0.292893219,7.50967674 L4.53553391,3.03084515 C4.9260582,2.61858008 5.55922318,2.61858008 5.94974747,3.03084515 C6.34027176,3.44311021 6.34027176,4.11152395 5.94974747,4.52378901 L2.41421356,8.25614867 Z M17.5857864,8.25614867 L14.0502525,4.52378901 C13.6597282,4.11152395 13.6597282,3.44311021 14.0502525,3.03084515 C14.4407768,2.61858008 15.0739418,2.61858008 15.4644661,3.03084515 L19.7071068,7.50967674 C20.0976311,7.9219418 20.0976311,8.59035554 19.7071068,9.0026206 L15.4644661,13.4814522 C15.0739418,13.8937173 14.4407768,13.8937173 14.0502525,13.4814522 C13.6597282,13.0691871 13.6597282,12.4007734 14.0502525,11.9885083 L17.5857864,8.25614867 Z"/>
        </svg>
    );

    const collapseIcon = (
        <svg className='code-control-icon' fill="#000000" viewBox="0 0 32 32" version="1.1" xmlns="http://www.w3.org/2000/svg">
            <title>collapse</title>
            <path d="M11.493 8.757l-3.454-3.453-2.665 2.665 3.454 3.453-2.59 2.59 7.797 0.004-0.017-7.784-2.525 2.525zM23.172 11.422l3.454-3.453-2.665-2.665-3.454 3.453-2.525-2.525-0.017 7.784 7.797-0.004-2.59-2.59zM8.828 20.578l-3.454 3.453 2.665 2.665 3.454-3.453 2.526 2.525 0.017-7.784-7.797 0.004 2.589 2.59zM25.762 17.988l-7.797-0.004 0.017 7.784 2.525-2.525 3.454 3.453 2.665-2.665-3.454-3.453 2.59-2.59z"/>
        </svg>
    );

    const runIcon = (
        <svg className="run-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M9.49997 12.4L5 17.7999" stroke="#333333" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M9.49997 12.4L5 7" stroke="#333333" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        <line x1="18" y1="18" x2="10" y2="18" stroke="#333333" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
    );

    const toggleExpand = () => setIsExpanded(!isExpanded);

    const runCode = async () => {
        setError('');
        
        if (currentCode.length > 5000) {
            setError("Code is too long. Maximum length is 5000 characters.");
            return;
        }

        try {
            const processedCode = currentCode.replace('{{INPUT}}', input);
            
            const response = await fetch("https://emkc.org/api/v2/piston/execute", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    language: "python",
                    version: "3.10.0",
                    files: [{ 
                        content: processedCode,
                        run_timeout: 3000,
                        compile_timeout: 3000,
                        compile_memory_limit: -1,
                        run_memory_limit: -1
                    }],
                }),
            });

            const result = await response.json();

            if (result.run.signal === "SIGKILL") {
                setError("Execution time limit exceeded or memory limit reached");
                return;
            }

            if (result.run.stderr) {
                setError(result.run.stderr);
                return;
            }

            setOutput(result.run.output);
        } catch (err) {
            setError("Failed to execute code: " + err.message);
        }
    };

    const debouncedRunCode = useCallback(
        debounce(() => {
            runCode();
        }, 1000),
        []
    );

    useEffect(() => {
        if (withInput) {
            const newCode = code.replace('{{INPUT}}', input);
            setCurrentCode(newCode);
        }
    }, [input, code, withInput]);

    const memoizedHighlightedCode = useMemo(() => {
        return highlightPythonSyntax(withInput ? currentCode : code);
    }, [currentCode, code, withInput]);

    const renderHighlightedCode = () => {
        return <div dangerouslySetInnerHTML={{ __html: memoizedHighlightedCode }} />;
    };

    return (
        <div className="python-container">
            {withInput && (
                <div className="input-container">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Enter input..."
                        className="message-input"
                    />
                </div>
            )}
            
            <div className={`code-display ${!isExpanded ? 'code-preview' : ''}`}>
                <div className="code-controls">
                    <button 
                        onClick={runCode}
                        className="run-control-button"
                        title="Run Code"
                    >
                        {runIcon}
                    </button>
                    <button 
                        onClick={toggleExpand}
                        className="code-control-button"
                        title={isExpanded ? "Collapse" : "Expand"}
                    >
                        {isExpanded ? collapseIcon : expandIcon}
                    </button>
                </div>
                <div className="code-content">
                    {renderHighlightedCode()}
                </div>
            </div>

            {error && (
                <div className="error-display">
                    {error}
                </div>
            )}
            
            {output && (
                <div className="output-display">
                    {output}
                </div>
            )}
        </div>
    );
};