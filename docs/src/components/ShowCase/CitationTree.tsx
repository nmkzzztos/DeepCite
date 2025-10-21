import { motion } from 'framer-motion';
import { BookOpen, Quote, CheckCircle, ArrowUpRight } from 'lucide-react';

export function CitationTree() {
    const citations = [
        {
            text: "For translation tasks, the Transformer can be trained significantly faster...",
            source: "Attention Is All You Need",
            page: "10",
            confidence: 95,
        },
        {
            text: "BERT advances the state of the art for eleven NLP tasks...",
            source: "BERT: Pre-training of Deep Bidirectional...",
            page: "2",
            confidence: 92,
        },
        {
            text: "On the WMT 2014 English-to-German translation task, the big...",
            source: "Attention Is All You Need",
            page: "8",
            confidence: 87,
        },
    ];

    return (
        <div className="relative w-full h-80 flex items-center justify-center">
            {/* Background tree pattern */}
            <div className="absolute inset-0 opacity-20">
                <svg width="100%" height="100%" className="absolute inset-0">
                    <defs>
                        <pattern id="tree-pattern" x="0" y="0" width="60" height="60" patternUnits="userSpaceOnUse">
                            <circle cx="30" cy="10" r="2" fill="currentColor" className="text-violet-400" />
                            <line x1="30" y1="12" x2="30" y2="50" stroke="currentColor" strokeWidth="1" className="text-violet-300" />
                            <line x1="30" y1="30" x2="15" y2="45" stroke="currentColor" strokeWidth="1" className="text-violet-300" />
                            <line x1="30" y1="30" x2="45" y2="45" stroke="currentColor" strokeWidth="1" className="text-violet-300" />
                            <circle cx="15" cy="45" r="1.5" fill="currentColor" className="text-violet-400" />
                            <circle cx="45" cy="45" r="1.5" fill="currentColor" className="text-violet-400" />
                        </pattern>
                    </defs>
                    <rect width="100%" height="100%" fill="url(#tree-pattern)" />
                </svg>
            </div>

            <div className="relative w-full max-w-md">
                {/* Main answer */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                    className="bg-gradient-to-r from-violet-50 to-fuchsia-50 border border-violet-200 rounded-xl p-4 mb-4 shadow-sm"
                >
                    <div className="flex items-start gap-3">
                        <img src="img/logo_mini.svg" alt="DeepCite Logo" className="w-7 h-7 flex-shrink-0" />
                        <div>
                            <div className="text-sm font-medium text-violet-800 mb-1">DeepCite Response</div>
                            <p className="text-sm text-gray-700 leading-relaxed">
                                The transformer architecture revolutionizes NLP through self-attention mechanisms,
                                enabling parallel processing and better context understanding <span className="text-violet-600">[1, S. 8, 10][2, S. 2]</span>.
                            </p>
                        </div>
                    </div>
                </motion.div>

                {/* Citations */}
                <div className="space-y-3">
                    {citations.map((citation, index) => (
                        <motion.div
                            key={index}
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: 0.6 + index * 0.2, duration: 0.5 }}
                            className="bg-white/90 backdrop-blur-sm border border-gray-200 rounded-lg p-3 shadow-sm"
                        >
                            <div className="flex items-start gap-2">
                                <Quote className="w-4 h-4 text-violet-500 mt-0.5 flex-shrink-0" />
                                <div className="flex-1 min-w-0">
                                    <p className="text-xs text-gray-700 leading-relaxed mb-2">
                                        "{citation.text.slice(0, 80)}..."
                                    </p>
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-2">
                                            <span className="text-xs font-medium text-violet-700">{citation.source}</span>
                                            <span className="text-xs text-gray-500">p.{citation.page}</span>
                                        </div>
                                        <div className="flex items-center gap-1">
                                            <div className="w-16 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                                                <motion.div
                                                    initial={{ width: 0 }}
                                                    animate={{ width: `${citation.confidence}%` }}
                                                    transition={{ delay: 1 + index * 0.2, duration: 0.8 }}
                                                    className="h-full bg-gradient-to-r from-violet-400 to-fuchsia-400 rounded-full"
                                                />
                                            </div>
                                            <span className="text-xs text-gray-600">{citation.confidence}%</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </motion.div>
                    ))}
                </div>

                {/* Export indicator */}
                <motion.div
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 2 }}
                    className="mt-4 flex items-center justify-center gap-2 bg-gradient-to-r from-violet-100 to-fuchsia-100 border border-violet-200 rounded-lg px-3 py-2"
                >
                    <ArrowUpRight className="w-4 h-4 text-violet-600" />
                    <span className="text-xs font-medium text-violet-700">Export Citations</span>
                </motion.div>
            </div>
        </div>
    );
}
