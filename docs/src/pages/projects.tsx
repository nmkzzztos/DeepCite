import React, { useState } from 'react';
import Layout from '@theme/Layout';
import clsx from 'clsx';
import styles from './projects.module.css';
import projectsData from './projects.json';

interface Project {
  id: string;
  title: string;
  authors: string;
  year: number;
  abstract: string;
  category: string;
  github?: string;
  demo?: string;
  docs?: string;
  stars?: number;
  license?: string;
  huggingface?: string;
}

const projects: Project[] = (projectsData as Project[]).sort((a, b) => b.year - a.year);
const categories = [...new Set(projects.map(project => project.category))];

function ProjectCard({ project }: { project: Project }) {
  const [isAbstractExpanded, setIsAbstractExpanded] = useState(false);

  const toggleAbstract = () => {
    setIsAbstractExpanded(!isAbstractExpanded);
  };

  return (
    <div className={styles.projectCard}>
      <div className={styles.projectContent}>
        <div className={styles.projectMain}>
          <h3 className={styles.projectTitle}>
            {project.github || project.huggingface ? (
              <a href={project.github || project.huggingface} target="_blank" rel="noopener noreferrer" className={styles.projectLink}>
                {project.title}
              </a>
            ) : (
              project.title
            )}
          </h3>
          <div className={styles.projectMeta}>
            {/* <span className={styles.authors}>{project.authors}</span> */}
            <div className={styles.projectMetaFooter}>
              <span className={styles.year}>({project.year}) </span>
              {project.license && (
                <span className={styles.license}>{project.license}</span>
              )}
              {project.stars && (
                <span className={styles.starsCount}>
                  ⭐ {project.stars.toLocaleString()} stars
                </span>
              )}
            </div>
          </div>
        </div>

        <div className={styles.projectLinks}>
          {project.github && (
            <a href={project.github} target="_blank" rel="noopener noreferrer" className={styles.link}>
              GitHub
            </a>
          )}
          {project.huggingface && (
            <a href={project.huggingface} target="_blank" rel="noopener noreferrer" className={styles.link}>
              Hugging Face
            </a>
          )}
          {project.docs && (
            <a href={project.docs} target="_blank" rel="noopener noreferrer" className={styles.link}>
              Docs
            </a>
          )}
          {project.demo && (
            <a href={project.demo} target="_blank" rel="noopener noreferrer" className={styles.link}>
              Demo
            </a>
          )}
          <button onClick={toggleAbstract} className={styles.toggleButton}>
            {isAbstractExpanded ? 'Hide description' : 'Show description'}
          </button>
        </div>
      </div>

      {isAbstractExpanded && (
        <div className={styles.abstractSection}>
          <p className={styles.abstract}>{project.abstract}</p>
        </div>
      )}
    </div>
  );
}

function CategorySection({ category, projects: categoryProjects }: { category: string; projects: Project[] }) {
  return (
    <section className={styles.categorySection}>
      <h2 className={styles.categoryTitle}>{category}</h2>
      <div className={styles.projectsGrid}>
        {categoryProjects.map(project => (
          <ProjectCard key={project.id} project={project} />
        ))}
      </div>
    </section>
  );
}

export default function Projects(): JSX.Element {
  return (
    <Layout
      title="Projects - DeepCite"
      description="Curated collection of influential AI/ML projects and tools for RAG, NLP, and agent development"
    >
      <div className={styles.container}>
        <header className={styles.header}>
          <h1 className={styles.title}>Projects</h1>
          <p className={styles.subtitle}>
            Curated collection of influential AI/ML projects and tools
          </p>
        </header>

        <main className={styles.main}>
          {categories.map(category => (
            <CategorySection
              key={category}
              category={category}
              projects={projects.filter(project => project.category === category)}
            />
          ))}
        </main>
      </div>
    </Layout>
  );
}
