import { motion } from 'framer-motion';

export function ContextNetwork() {
    return (
        <div className="relative w-full h-80 flex items-center justify-center">
            {/* Background network pattern */}
            <div className="absolute inset-0 opacity-20">
                <svg width="100%" height="100%" className="absolute inset-0">
                    <defs>
                        <pattern id="network-pattern" x="0" y="0" width="40" height="40" patternUnits="userSpaceOnUse">
                            <circle cx="20" cy="20" r="1" fill="currentColor" className="text-emerald-400" />
                            <line x1="20" y1="20" x2="40" y2="20" stroke="currentColor" strokeWidth="0.5" className="text-emerald-300" />
                            <line x1="20" y1="20" x2="20" y2="40" stroke="currentColor" strokeWidth="0.5" className="text-emerald-300" />
                        </pattern>
                    </defs>
                    <rect width="100%" height="100%" fill="url(#network-pattern)" />
                </svg>
            </div>

            <motion.img
                src="img/contextNetwork.svg"
                alt="Context Network"
                className="w-full h-full object-contain"
                initial={{ opacity: 0, scale: 0.4 * 0.8 }}
                animate={{ opacity: 1, scale: 0.8 }}
                transition={{ duration: 0.8, ease: 'easeOut' }}
            />
        </div>
    );
}
