import React, { useState } from 'react';
import Layout from '@theme/Layout';
import clsx from 'clsx';
import { CitationProvider, Citation, References } from '../components/Citation/Citation';
import styles from './papers.module.css';
import papersData from './papers.json';

interface Paper {
  id: string;
  title: string;
  authors: string;
  year: number;
  journal?: string;
  abstract: string;
  category: string;
  url?: string;
  doi?: string;
  arxiv?: string;
  pdf?: string;
  citations?: number;
}

type CitationFormat = 'bibtex' | 'apa' | 'mla' | 'chicago';

const papers: Paper[] = papersData.sort((a, b) => b.year - a.year);
const categories = [...new Set(papers.map(paper => paper.category))];

// Citation formatting functions
const generateBibTeX = (paper: Paper): string => {
  const authorList = paper.authors.split(', ').join(' and ');
  const entry = paper.journal ? 'article' : 'misc';
  
  let bibtex = `@${entry}{${paper.id},\n`;
  bibtex += `  author = {${authorList}},\n`;
  bibtex += `  title = {${paper.title}},\n`;
  bibtex += `  year = {${paper.year}},\n`;
  
  if (paper.journal) {
    bibtex += `  journal = {${paper.journal}},\n`;
  }
  if (paper.doi) {
    bibtex += `  doi = {${paper.doi}},\n`;
  }
  if (paper.arxiv) {
    bibtex += `  eprint = {${paper.arxiv}},\n`;
    bibtex += `  archivePrefix = {arXiv},\n`;
  }
  if (paper.url) {
    bibtex += `  url = {${paper.url}},\n`;
  }
  
  bibtex += `}`;
  return bibtex;
};

const generateAPA = (paper: Paper): string => {
  const authors = paper.authors.split(', ');
  const formattedAuthors = authors.length > 7 
    ? `${authors.slice(0, 6).join(', ')}, ... ${authors[authors.length - 1]}`
    : authors.join(', ');
  
  let citation = `${formattedAuthors} (${paper.year}). ${paper.title}. `;
  
  if (paper.journal) {
    citation += `${paper.journal}. `;
  }
  if (paper.doi) {
    citation += `https://doi.org/${paper.doi}`;
  } else if (paper.url) {
    citation += paper.url;
  }
  
  return citation;
};

const generateMLA = (paper: Paper): string => {
  const authors = paper.authors.split(', ');
  const firstAuthor = authors[0];
  const formattedAuthors = authors.length > 1 
    ? `${firstAuthor}, et al.`
    : firstAuthor;
  
  let citation = `${formattedAuthors} "${paper.title}." `;
  
  if (paper.journal) {
    citation += `${paper.journal}, `;
  }
  citation += `${paper.year}. `;
  
  if (paper.url) {
    citation += `<${paper.url}>`;
  }
  
  return citation;
};

const generateChicago = (paper: Paper): string => {
  const authors = paper.authors.split(', ');
  const firstAuthor = authors[0];
  const formattedAuthors = authors.length > 1 
    ? `${firstAuthor}, et al.`
    : firstAuthor;
  
  let citation = `${formattedAuthors}. "${paper.title}." `;
  
  if (paper.journal) {
    citation += `${paper.journal} `;
  }
  citation += `(${paper.year})`;
  
  if (paper.doi) {
    citation += `. https://doi.org/${paper.doi}`;
  } else if (paper.url) {
    citation += `. ${paper.url}`;
  }
  
  return citation;
};

const getCitation = (paper: Paper, format: CitationFormat): string => {
  switch (format) {
    case 'bibtex':
      return generateBibTeX(paper);
    case 'apa':
      return generateAPA(paper);
    case 'mla':
      return generateMLA(paper);
    case 'chicago':
      return generateChicago(paper);
    default:
      return generateBibTeX(paper);
  }
};

function PaperCard({ paper }: { paper: Paper }) {
  const [isAbstractExpanded, setIsAbstractExpanded] = useState(false);
  const [isCitationExpanded, setIsCitationExpanded] = useState(false);
  const [selectedFormat, setSelectedFormat] = useState<CitationFormat>('bibtex');
  const [copySuccess, setCopySuccess] = useState(false);

  const toggleAbstract = () => {
    setIsAbstractExpanded(!isAbstractExpanded);
  };

  const toggleCitation = () => {
    setIsCitationExpanded(!isCitationExpanded);
    setCopySuccess(false);
  };

  const copyCitation = async () => {
    const citation = getCitation(paper, selectedFormat);
    try {
      await navigator.clipboard.writeText(citation);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    } catch (err) {
      console.error('Failed to copy citation:', err);
    }
  };

  return (
    <div className={styles.paperCard}>
      <div className={styles.paperContent}>
        <div className={styles.paperMain}>
          <h3 className={styles.paperTitle}>
            {paper.url ? (
              <a href={paper.url} target="_blank" rel="noopener noreferrer" className={styles.paperLink}>
                {paper.title}
              </a>
            ) : (
              paper.title
            )}
          </h3>
          <div className={styles.paperMeta}>
            <span className={styles.authors}>{paper.authors}</span>
            <div className={styles.paperMetaFooter}>
              <span className={styles.year}>({paper.year}) </span>
              {paper.journal && <span className={styles.journal}>{paper.journal}</span>}
              {paper.citations && (
                <span className={styles.citationsCount}>
                  {paper.citations.toLocaleString()} citations
                </span>
              )}
            </div>
          </div>
        </div>

        <div className={styles.paperLinks}>
          {paper.arxiv && (
            <a href={`https://arxiv.org/abs/${paper.arxiv}`} target="_blank" rel="noopener noreferrer" className={styles.link}>
              arXiv
            </a>
          )}
          {paper.pdf && (
            <a href={paper.pdf} target="_blank" rel="noopener noreferrer" className={styles.link}>
              PDF
            </a>
          )}
          {paper.doi && (
            <a href={`https://doi.org/${paper.doi}`} target="_blank" rel="noopener noreferrer" className={styles.link}>
              DOI
            </a>
          )}
          <button onClick={toggleCitation} className={styles.citeButton}>
            Cite
          </button>
          <button onClick={toggleAbstract} className={styles.toggleButton}>
            {isAbstractExpanded ? 'Hide abstract' : 'Show abstract'}
          </button>
        </div>
      </div>

      {isAbstractExpanded && (
        <div className={styles.abstractSection}>
          <p className={styles.abstract}>{paper.abstract}</p>
        </div>
      )}

      {isCitationExpanded && (
        <div className={styles.citationSection}>
          <div className={styles.citationHeader}>
            <div className={styles.formatSelector}>
              <button
                className={`${styles.formatButton} ${selectedFormat === 'bibtex' ? styles.formatButtonActive : ''}`}
                onClick={() => setSelectedFormat('bibtex')}
              >
                BibTeX
              </button>
              <button
                className={`${styles.formatButton} ${selectedFormat === 'apa' ? styles.formatButtonActive : ''}`}
                onClick={() => setSelectedFormat('apa')}
              >
                APA
              </button>
              <button
                className={`${styles.formatButton} ${selectedFormat === 'mla' ? styles.formatButtonActive : ''}`}
                onClick={() => setSelectedFormat('mla')}
              >
                MLA
              </button>
              <button
                className={`${styles.formatButton} ${selectedFormat === 'chicago' ? styles.formatButtonActive : ''}`}
                onClick={() => setSelectedFormat('chicago')}
              >
                Chicago
              </button>
            </div>
            <button onClick={copyCitation} className={styles.copyButton}>
              {copySuccess ? '✓ Copied!' : 'Copy'}
            </button>
          </div>
          <pre className={styles.citationText}>
            {getCitation(paper, selectedFormat)}
          </pre>
        </div>
      )}
    </div>
  );
}

function CategorySection({ category, papers: categoryPapers }: { category: string; papers: Paper[] }) {
  return (
    <section className={styles.categorySection}>
      <h2 className={styles.categoryTitle}>{category}</h2>
      <div className={styles.papersGrid}>
        {categoryPapers.map(paper => (
          <PaperCard key={paper.id} paper={paper} />
        ))}
      </div>
    </section>
  );
}

export default function Papers(): JSX.Element {
  return (
    <CitationProvider>
      <Layout
        title="Papers - DeepCite"
        description="Curated collection of influential scientific papers across AI, quantum computing, cryptography, and NLP"
      >
        <div className={styles.container}>
          <header className={styles.header}>
            <h1 className={styles.title}>Papers</h1>
            <p className={styles.subtitle}>
              Curated collection of influential research papers across LLM, RAG, Agentic AI, etc.
            </p>
          </header>

          <main className={styles.main}>
            {categories.map(category => (
              <CategorySection
                key={category}
                category={category}
                papers={papers.filter(paper => paper.category === category)}
              />
            ))}
          </main>

          <References />
        </div>
      </Layout>
    </CitationProvider>
  );
}
