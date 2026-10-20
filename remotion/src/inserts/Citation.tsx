import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import {apparition, momentsImages, progression} from '../anim';
import {tailleTexte} from '../Carte';
import {alpha, Couleurs} from '../theme';

// 1. Citation : la phrase s'écrit mot par mot, puis le nom de l'auteur.
export const Citation: React.FC<{texte: string; auteur?: string; moments?: number[]; couleurs: Couleurs}> = ({
	texte,
	auteur,
	moments,
	couleurs,
}) => {
	const frame = useCurrentFrame();
	const {fps, durationInFrames} = useVideoConfig();
	const mots = texte.split(/\s+/).filter(Boolean);
	const debuts = momentsImages(mots.length, fps, durationInFrames, moments, 0.4, 1.3).map((d, i, l) =>
		// jamais plus rapide qu'un mot toutes les 2 images
		i === 0 ? d : Math.max(d, l[0] + i * 2),
	);
	const finTexte = debuts[debuts.length - 1] ?? 0;
	const taille = tailleTexte(texte, 72, 44, 110);
	const guillemet = progression(frame, 2, Math.round(0.5 * fps));
	return (
		<div style={{display: 'flex', flexDirection: 'column', gap: 26}}>
			<div
				style={{
					fontWeight: 800,
					fontSize: 150,
					lineHeight: 0.6,
					height: 62,
					color: couleurs.bleu,
					opacity: guillemet,
					scale: String(0.7 + 0.3 * guillemet),
					transformOrigin: 'left top',
				}}
			>
				“
			</div>
			<div style={{fontWeight: 700, fontSize: taille, lineHeight: 1.18, letterSpacing: -0.5}}>
				{mots.map((m, i) => (
					<span key={i} style={{display: 'inline-block', marginRight: '0.26em', ...apparition(frame, debuts[i], 7, 12)}}>
						{m}
					</span>
				))}
			</div>
			{auteur ? (
				<div style={{display: 'flex', alignItems: 'center', gap: 18, marginTop: 6}}>
					<div
						style={{
							height: 4,
							borderRadius: 2,
							background: couleurs.bleu,
							width: 64 * progression(frame, finTexte + 6, 12),
						}}
					/>
					<div
						style={{
							fontWeight: 600,
							fontSize: 32,
							letterSpacing: 2,
							textTransform: 'uppercase',
							color: alpha(couleurs.blanc, 0.75),
							...apparition(frame, finTexte + 12, 10, 10),
						}}
					>
						{auteur}
					</div>
				</div>
			) : null}
		</div>
	);
};
