import { motion } from 'framer-motion';
import { FileText, Upload, Database, ArrowRight } from 'lucide-react';

export function DocumentFlow() {
    const documents = [
        { name: 'attention_is_all_you_need.pdf', type: 'PDF', pages: 16 },
        { name: 'chain_of_thought_reasoning.pdf', type: 'PDF', pages: 43 },
        { name: 'bert_paper.pdf', type: 'PDF', pages: 16 },
    ];

    return (
        <div className="relative w-full h-80 flex items-center justify-center">
            {/* Background grid */}
            <div className="absolute inset-0 opacity-30">
                <div className="absolute inset-0" style={{
                    backgroundImage: `
            linear-gradient(to right, rgba(59, 130, 246, 0.1) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(59, 130, 246, 0.1) 1px, transparent 1px)
          `,
                    backgroundSize: '20px 20px'
                }} />
            </div>

            {/* Documents flowing to workspace */}
            <div className="relative flex items-center gap-8">
                {/* Source documents */}
                <div className="flex flex-col gap-2">
                    {documents.map((doc, index) => (
                        <motion.div
                            key={doc.name}
                            initial={{ x: -50, opacity: 0 }}
                            animate={{ x: 0, opacity: 1 }}
                            transition={{ delay: index * 0.2, duration: 0.6 }}
                            className="flex items-center gap-2 bg-white/80 backdrop-blur-sm border border-blue-200 rounded-lg p-2 shadow-sm"
                        >
                            <FileText className="w-4 h-4 text-blue-600" />
                            <div className="text-xs">
                                <div className="font-medium text-gray-800 truncate max-w-24">{doc.name}</div>
                                <div className="text-gray-500">{doc.pages} pages</div>
                            </div>
                        </motion.div>
                    ))}
                </div>

                {/* Upload arrow */}
                <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ delay: 0.8, type: 'spring', stiffness: 200 }}
                    className="flex flex-col items-center gap-2"
                >
                    <Upload className="w-6 h-6 text-blue-600" />
                </motion.div>

                {/* Workspace */}
                <motion.div
                    initial={{ scale: 0.8, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ delay: 1, duration: 0.6 }}
                    className="bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-200 rounded-xl p-4 shadow-lg"
                >
                    <div className="flex items-center gap-2 mb-3">
                        <Database className="w-5 h-5 text-blue-600" />
                        <span className="text-sm font-semibold text-blue-800">Research Workspace</span>
                    </div>

                    <div className="space-y-2">
                        {documents.map((doc, index) => (
                            <motion.div
                                key={`processed-${doc.name}`}
                                initial={{ x: 20, opacity: 0 }}
                                animate={{ x: 0, opacity: 1 }}
                                transition={{ delay: 1.2 + index * 0.1, duration: 0.4 }}
                                className="flex items-center gap-2 bg-white/60 rounded-md p-2 text-xs"
                            >
                                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                                <span className="text-gray-700 truncate max-w-32">{doc.name.replace('.pdf', '')}</span>
                                <span className="text-gray-500 ml-auto">✓</span>
                            </motion.div>
                        ))}
                    </div>

                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 1.8 }}
                        className="mt-3 text-xs text-blue-600 font-medium"
                    >
                        Paragraph-level parsing ready
                    </motion.div>
                </motion.div>
            </div>
        </div>
    );
}
