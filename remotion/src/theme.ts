import {loadFont} from '@remotion/fonts';
import {staticFile} from 'remotion';

// Les polices sont copiées depuis assets/fonts/ par le script de rendu.
const poids: [string, string][] = [
	['500', 'InterDisplay-Medium.ttf'],
	['600', 'InterDisplay-SemiBold.ttf'],
	['700', 'InterDisplay-Bold.ttf'],
	['800', 'InterDisplay-ExtraBold.ttf'],
];
for (const [weight, fichier] of poids) {
	loadFont({family: 'Inter Display', url: staticFile(`fonts/${fichier}`), weight});
}

export const POLICE = '"Inter Display", sans-serif';

export type Couleurs = {
	anthracite: string;
	carte: string;
	bleu: string;
	blanc: string;
};

export const COULEURS_DEFAUT: Couleurs = {
	anthracite: '#111318',
	carte: '#1A1D25',
	bleu: '#246BFD',
	blanc: '#FFFFFF',
};

// Transparence d'une couleur #RRGGBB (ex: blanc à 60 %)
export const alpha = (hex: string, a: number) => {
	const n = parseInt(hex.slice(1), 16);
	return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
};
