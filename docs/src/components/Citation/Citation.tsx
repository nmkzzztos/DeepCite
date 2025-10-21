import React, { createContext, useContext, useState, useEffect } from "react";
import "./Citation.css";
import { parseBibTeX } from './BibParser';
import * as R from './BibTex';
import { useLocation } from "@docusaurus/router";

const CitationContext = createContext<{
    citations: Array<any>;
    addCitation: (id: string, reference: any) => void;
    references: Record<string, any>;
}>(null!);

export const CitationProvider = ({ children }) => {
    const [citations, setCitations] = useState([]);
    const [references, setReferences] = useState<Record<string, any>>({});
    const location = useLocation();
    
    useEffect(() => {
        const path = location.pathname
            .split('/')
            .filter(Boolean)
            .slice(1)
            .map(part => part.charAt(0).toUpperCase() + part.slice(1))
            .join('');

        console.log(path);
        
        const bibContent = R[path];
        if (bibContent) {
            const refs = parseBibTeX(bibContent);
            setReferences(refs);
        }
    }, [location]);

    const addCitation = (id, reference) => {
        setCitations((prev) =>
            prev.some((item) => item.id === id) ? prev : [...prev, { id, ...reference }]
        );
    };

    return (
        <CitationContext.Provider value={{ citations, addCitation, references }}>
            {children}
        </CitationContext.Provider>
    );
};


const useCitations = () => useContext(CitationContext);

export const Citation = ({ id }: { id: string }) => {
    const { addCitation, references } = useCitations();
    const citation = references[id];
    
    useEffect(() => {
        if (citation) {
            addCitation(id, citation);
        }
    }, [id, citation, addCitation]);
    
    if (!citation) return null;
    
    const formatAuthorDisplay = (authorString: string) => {
        const authors = authorString.split(' and ').join(', ').split(', ');
        if (authors.length <= 2) {
            return authorString;
        }
        const firstAuthor = authors[0].trim().split(' ').pop();
        return `${firstAuthor} et al.`;
    };

    const authorDisplay = formatAuthorDisplay(citation.author);

    const handleClick = () => {
        const element = document.getElementById(`ref-${id}`);
        if (element) {
            const viewportHeight = window.innerHeight;
            const elementRect = element.getBoundingClientRect();
            const absoluteElementTop = window.pageYOffset + elementRect.top;
            const middle = absoluteElementTop - (viewportHeight / 2);
            
            window.scrollTo({
                top: middle,
                behavior: 'smooth'
            });

            element.classList.add('reference-highlight');
            setTimeout(() => {
                element.classList.remove('reference-highlight');
            }, 2000);
        }
    };

    return (
        <span 
            className="citation" 
            onClick={handleClick} 
            role="button" 
            tabIndex={0}
            onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    handleClick();
                }
            }}
        >
            [{authorDisplay} {citation.year}]
        </span>
    );
};

export const References = () => {
    const { citations } = useCitations();

    if (!citations || citations.length === 0) return null;

    return (
        <div className="references-section">
            <h2>References</h2>
            <ol>
                {citations.map((ref) => (
                    <li key={ref.id} id={`ref-${ref.id}`}>
                        {ref.author}{ref.author.endsWith('.') ? '' : '.'} {' '}
                        {ref.url ? (
                            <a href={ref.url} target="_blank" rel="noopener noreferrer">
                                {ref.title}
                            </a>
                        ) : (
                            ref.title
                        )},
                        {ref.journal && <em> {ref.journal}</em>}
                        {ref.volume && <>, {ref.volume}</>}
                        {ref.pages && <>, {ref.pages}</>} ({ref.year})
                    </li>
                ))}
            </ol>
        </div>
    );
};
