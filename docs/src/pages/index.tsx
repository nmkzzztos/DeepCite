import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';
import { motion } from 'framer-motion';
import { ArrowRight, Sparkles, CheckCircle2, Database, Target, Award, FileText, BookOpen } from 'lucide-react';
import { DocumentFlow } from '../components/ShowCase/DocumentFlow';
import { ContextNetwork } from '../components/ShowCase/ContextNetwork';
import { CitationTree } from '../components/ShowCase/CitationTree';

import styles from './index.module.css';

function HomepageHeader() {
  const {siteConfig} = useDocusaurusContext();

  return (
    <header className={clsx('hero', styles.heroBanner)}>
      <div className="container">
        <div className={styles.heroContent}>
          <div className={styles.heroLeft}>
            <div className={styles.logoContainer}>
              <img src="img/logo_white.svg" style={{width: '250px'}} alt="DeepCite Logo" />
            </div>
            <p className={styles.heroDescription}>
              Transform large collections of research papers into structured knowledge.
              DeepCite automatically segments every upload into paragraphs, enriches metadata,
              and prepares each citation for retrieval-augmented generation.
            </p>
            <div className={styles.buttons}>
              <Link
                className="button button--primary button--lg"
                to="/attention.pdf">
                <FileText size={20} />
                Paper
              </Link>
              <Link
                className="button button--outline button--secondary button--lg"
                to="/docs/Backend/introduction">
                <BookOpen size={20} />
                Documentation
              </Link>
            </div>
            <div className={styles.statsContainer}>
              <div className={styles.stat}>
                <div className={styles.statValue}>1-2 min</div>
                <div className={styles.statLabel}>To ingest an arXiv paper</div>
              </div>
              <div className={styles.stat}>
                <div className={styles.statValue}>Paragraph</div>
                <div className={styles.statLabel}>Level RAG context</div>
              </div>
              <div className={styles.stat}>
                <div className={styles.statValue}>Scholarly</div>
                <div className={styles.statLabel}>Citations preserved</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}

function ShowcaseSection() {
  const features = [
    {
      title: 'Load Research Papers into Workspaces',
      description:
        'Drag-and-drop arXiv PDFs or conference proceedings into a workspace. DeepCite parses each document into paragraph-level units, preserving formulas, tables, and references for downstream retrieval.',
      icon: Database,
      component: DocumentFlow,
      gradient: 'from-blue-500/10 to-purple-500/10',
      borderColor: 'border-blue-400/20',
      details: [
        'Automatic paragraph segmentation ready for RAG pipelines',
        'Metadata enrichment for authors, venues, and publication year'
      ],
    },
    {
      title: 'Curate the Exact Scientific Context',
      description:
        'Target the conversation to the workspaces, documents, or even specific pages that matter. Compare different architectures, align methodologies, and isolate key insights without losing track of the surrounding narrative.',
      icon: Target,
      component: ContextNetwork,
      gradient: 'from-emerald-500/10 to-teal-500/10',
      borderColor: 'border-emerald-400/20',
      details: [
        'Mix and match workspaces focused on different research domains',
        'Lock conversations to selected documents or page ranges'
      ],
    },
    {
      title: 'Get Journal-Grade Answers with Citations',
      description:
        "DeepCite's LLM responds with structured arguments that read like a peer-reviewed discussion section, complete with inline citations and page references for every claim.",
      icon: Award,
      component: CitationTree,
      gradient: 'from-violet-500/10 to-fuchsia-500/10',
      borderColor: 'border-violet-400/20',
      details: [
        'Evidence trails show which paper, section, and page informed each insight',
        'Exportable citation formats built for literature reviews'
      ],
    },
  ];

  return (
    <section className="relative overflow-hidden">
      {/* Animated Background Elements */}
      <div className="absolute inset-0 pointer-events-none">
        {[...Array(20)].map((_, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0 }}
            animate={{
              opacity: [0.1, 0.3, 0.1],
              scale: [1, 1.2, 1],
            }}
            transition={{
              duration: 3 + Math.random() * 2,
              repeat: Infinity,
              delay: Math.random() * 2,
            }}
            className="absolute w-1 h-1 bg-primary/20 rounded-full"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
            }}
          />
        ))}
      </div>

      {/* Features Section */}
      <div className="max-w-7xl mx-auto px-6 py-20">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl font-bold mb-4">Powerful Features for Researchers</h2>
          <p className="text-muted-foreground max-w-2xl mx-auto text-lg">
            Everything you need to accelerate your research workflow
          </p>
        </motion.div>

        <div className="space-y-32">
          {features.map((feature, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-100px' }}
              transition={{ duration: 0.8, delay: 0.2 }}
              className={`relative grid lg:grid-cols-2 gap-12 items-center ${
                index % 2 === 1 ? 'lg:flex-row-reverse' : ''
              }`}
            >
              {/* Content */}
              <div className={`space-y-6 ${index % 2 === 1 ? 'lg:order-2' : ''}`}>
                <div className={`inline-flex items-center gap-3 px-4 py-2 rounded-xl bg-gradient-to-r ${feature.gradient} border ${feature.borderColor}`}>
                  <feature.icon className="w-5 h-5" />
                  <span className="text-sm font-medium">Feature {index + 1}</span>
                </div>

                <h3 className="text-2xl font-bold">{feature.title}</h3>

                <p className="text-muted-foreground leading-relaxed text-lg">{feature.description}</p>

                <ul className="space-y-3">
                  {feature.details.map((detail, idx) => (
                    <motion.li
                      key={idx}
                      initial={{ opacity: 0, x: -20 }}
                      whileInView={{ opacity: 1, x: 0 }}
                      viewport={{ once: true }}
                      transition={{ delay: 0.3 + idx * 0.1 }}
                      className="flex items-start gap-3"
                    >
                      <CheckCircle2 className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                      <span className="text-sm text-muted-foreground">{detail}</span>
                    </motion.li>
                  ))}
                </ul>
              </div>

              {/* Visual Component */}
              <div className={`${index % 2 === 1 ? 'lg:order-1' : ''}`}>
                <motion.div
                  initial={{ opacity: 0, scale: 0.9 }}
                  whileInView={{ opacity: 1, scale: 1 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.8, delay: 0.3 }}
                  className={`relative rounded-2xl bg-gradient-to-br ${feature.gradient} border ${feature.borderColor} p-8 backdrop-blur-sm shadow-xl`}
                >
                  <div className="absolute inset-0 bg-grid-white/5 rounded-2xl" />
                  <feature.component />
                </motion.div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

export default function Home(): JSX.Element {
  return (
    <Layout
      title={`DeepCite - AI Research Assistant`}
      description="Transform your research workflow with DeepCite - an AI-powered assistant for scientists. Create workspaces, upload papers, and engage in intelligent conversations about scientific literature.">
      <HomepageHeader />
      <main>
        <ShowcaseSection />
      </main>
    </Layout>
  );
}
