interface BibEntry {
    id: string;
    type: string;
    fields: Record<string, string>;
}

export function parseBibTeX(bibtex: string): Record<string, any> {
    const entries: Record<string, any> = {};
    
    const entryRegex = /@(\w+)\s*{\s*([^,]+),([^@]+)}/g;
    const fieldRegex = /(\w+)\s*=\s*{([^}]+)}/g;

    let match;
    while ((match = entryRegex.exec(bibtex)) !== null) {
        const [_, type, id, content] = match;
        const fields: Record<string, string> = {};
        
        let fieldMatch;
        while ((fieldMatch = fieldRegex.exec(content)) !== null) {
            const [_, key, value] = fieldMatch;
            fields[key.toLowerCase()] = value.trim();
        }

        entries[id] = {
            ...fields,
            id,
            type: type.toLowerCase()
        };
    }

    return entries;
}

export async function parseBibTeXFile(filePath: string): Promise<Record<string, any>> {
    const response = await fetch(filePath);
    const bibtex = await response.text();
    return parseBibTeX(bibtex);
}