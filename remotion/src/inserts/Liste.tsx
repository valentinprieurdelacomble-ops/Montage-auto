import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import {apparition, momentsImages, progression} from '../anim';
import {alpha, Couleurs} from '../theme';

// 4. Liste : les points apparaissent au rythme de la voix.
export const Liste: React.FC<{titre?: string; elements: string[]; moments?: number[]; couleurs: Couleurs}> = ({
	titre,
	elements,
	moments,
	couleurs,
}) => {
	const frame = useCurrentFrame();
	const {fps, durationInFrames} = useVideoConfig();
	const debuts = momentsImages(elements.length, fps, durationInFrames, moments, 0.45, 1.0);
	const taille = elements.length > 3 ? 44 : 52;
	return (
		<div style={{display: 'flex', flexDirection: 'column', gap: 30}}>
			{titre ? (
				<div style={{fontWeight: 800, fontSize: 50, letterSpacing: -0.5, marginBottom: 6, ...apparition(frame, 4, 10)}}>
					{titre}
				</div>
			) : null}
			{elements.map((e, i) => {
				const p = progression(frame, debuts[i], 10);
				return (
					<div
						key={i}
						style={{display: 'flex', alignItems: 'center', gap: 26, opacity: p, translate: `${(1 - p) * -34}px 0px`}}
					>
						<div
							style={{
								flex: 'none',
								width: 72,
								height: 72,
								borderRadius: 72,
								background: couleurs.bleu,
								display: 'flex',
								alignItems: 'center',
								justifyContent: 'center',
								fontWeight: 800,
								fontSize: 34,
								scale: String(0.6 + 0.4 * p),
								boxShadow: `0 6px 18px ${alpha(couleurs.bleu, 0.35)}`,
							}}
						>
							{i + 1}
						</div>
						<div style={{fontWeight: 700, fontSize: taille, lineHeight: 1.15}}>{e}</div>
					</div>
				);
			})}
		</div>
	);
};
