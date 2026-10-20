import {Easing, interpolate} from 'remotion';

const DOUX = Easing.bezier(0.16, 1, 0.3, 1);

// Valeur qui passe de 0 à 1 entre `debut` et `debut + duree` (en images), avec une courbe douce.
export const progression = (frame: number, debut: number, duree: number) =>
	interpolate(frame, [debut, debut + duree], [0, 1], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
		easing: DOUX,
	});

// Apparition standard d'un élément : fondu + légère montée.
export const apparition = (frame: number, debut: number, duree = 10, decalage = 18) => {
	const p = progression(frame, debut, duree);
	return {opacity: p, translate: `0px ${(1 - p) * decalage}px`};
};

// Moments d'apparition (en images) de n éléments : ceux fournis, sinon répartis régulièrement.
export const momentsImages = (
	n: number,
	fps: number,
	total: number,
	moments?: number[],
	debut = 0.35,
	finMarge = 1.0,
) => {
	if (moments && moments.length >= n) {
		return moments.slice(0, n).map((s) => Math.round(s * fps));
	}
	const pas = Math.max(0.12, Math.min(0.9, (total / fps - debut - finMarge) / Math.max(1, n)));
	return Array.from({length: n}, (_, i) => Math.round((debut + i * pas) * fps));
};
