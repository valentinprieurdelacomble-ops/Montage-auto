import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import {apparition, momentsImages, progression} from '../anim';
import {alpha, Couleurs} from '../theme';

// 3. Schéma en 3 étapes : trois blocs reliés par une ligne qui se trace.
export const Etapes: React.FC<{titre?: string; elements: string[]; moments?: number[]; couleurs: Couleurs}> = ({
	titre,
	elements,
	moments,
	couleurs,
}) => {
	const frame = useCurrentFrame();
	const {fps, durationInFrames} = useVideoConfig();
	const n = Math.max(1, elements.length);
	const debuts = momentsImages(n, fps, durationInFrames, moments, 0.45, 1.2);
	const rond = 92;
	// position de la ligne : de 0 (1re étape) à 1 (dernière étape), atteint chaque étape à son moment
	const avancement = (() => {
		if (n === 1) return 1;
		for (let i = n - 1; i >= 1; i--) {
			if (frame >= debuts[i - 1]) {
				const p = progression(frame, debuts[i - 1], Math.max(6, debuts[i] - debuts[i - 1]));
				return (i - 1 + p) / (n - 1);
			}
		}
		return 0;
	})();
	return (
		<div style={{display: 'flex', flexDirection: 'column', gap: 34}}>
			{titre ? (
				<div style={{fontWeight: 800, fontSize: 48, letterSpacing: -0.5, ...apparition(frame, 4, 10)}}>{titre}</div>
			) : null}
			<div style={{position: 'relative'}}>
				{/* ligne de fond + ligne bleue qui se trace */}
				<div
					style={{
						position: 'absolute',
						top: rond / 2 - 2,
						left: `${50 / n}%`,
						width: `${100 - 100 / n}%`,
						height: 4,
						borderRadius: 2,
						background: alpha(couleurs.blanc, 0.1),
					}}
				>
					<div style={{height: '100%', width: `${avancement * 100}%`, background: couleurs.bleu, borderRadius: 2}} />
				</div>
				<div style={{display: 'flex'}}>
					{elements.map((e, i) => {
						const p = progression(frame, debuts[i], 9);
						return (
							<div key={i} style={{flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 22}}>
								<div
									style={{
										width: rond,
										height: rond,
										borderRadius: rond,
										boxSizing: 'border-box',
										border: `4px solid ${couleurs.bleu}`,
										background: p > 0.5 ? couleurs.bleu : couleurs.carte,
										display: 'flex',
										alignItems: 'center',
										justifyContent: 'center',
										fontWeight: 800,
										fontSize: 42,
										scale: String(0.4 + 0.6 * p),
										opacity: Math.min(1, p * 2),
										position: 'relative',
									}}
								>
									{i + 1}
								</div>
								<div
									style={{
										fontWeight: 700,
										fontSize: e.length > 22 ? 34 : 40,
										lineHeight: 1.18,
										textAlign: 'center',
										padding: '0 6px',
										...apparition(frame, debuts[i] + 3, 10, 14),
									}}
								>
									{e}
								</div>
							</div>
						);
					})}
				</div>
			</div>
		</div>
	);
};
