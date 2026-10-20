import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {progression} from './anim';
import {alpha, Couleurs, POLICE} from './theme';

// Carte à coins arrondis, ombre légère, qui apparaît en douceur.
export const Carte: React.FC<{couleurs: Couleurs; children: React.ReactNode}> = ({couleurs, children}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const p = progression(frame, 0, Math.round(0.45 * fps));
	return (
		<AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', padding: '36px 60px'}}>
			<div
				style={{
					width: '100%',
					height: '100%',
					borderRadius: 40,
					background: `linear-gradient(160deg, ${couleurs.carte} 0%, ${alpha(couleurs.carte, 0.96)} 100%)`,
					border: `1.5px solid ${alpha(couleurs.blanc, 0.07)}`,
					boxShadow: `0 24px 60px ${alpha('#000000', 0.45)}, 0 2px 0 ${alpha(couleurs.blanc, 0.04)} inset`,
					opacity: p,
					scale: String(0.94 + 0.06 * p),
					translate: `0px ${(1 - p) * 26}px`,
					padding: '44px 56px',
					boxSizing: 'border-box',
					display: 'flex',
					flexDirection: 'column',
					justifyContent: 'center',
					fontFamily: POLICE,
					color: couleurs.blanc,
					overflow: 'hidden',
					position: 'relative',
				}}
			>
				{/* fin liseré bleu en haut de la carte, qui se trace */}
				<div
					style={{
						position: 'absolute',
						top: 0,
						left: 0,
						height: 5,
						width: `${100 * progression(frame, 4, Math.round(0.8 * fps))}%`,
						background: couleurs.bleu,
					}}
				/>
				{children}
			</div>
		</AbsoluteFill>
	);
};

// Petite étiquette en capitales (ex: AVANT, APRÈS)
export const Etiquette: React.FC<{texte: string; couleur: string; style?: React.CSSProperties}> = ({
	texte,
	couleur,
	style,
}) => (
	<div style={{fontWeight: 700, fontSize: 28, letterSpacing: 4, color: couleur, textTransform: 'uppercase', ...style}}>
		{texte}
	</div>
);

// Taille de texte adaptée à la longueur (le texte doit toujours tenir dans la carte)
export const tailleTexte = (texte: string, grand: number, petit: number, longueurMax = 90) => {
	const n = texte.length;
	if (n <= 28) return grand;
	return Math.max(petit, Math.round(grand - ((grand - petit) * (n - 28)) / (longueurMax - 28)));
};
