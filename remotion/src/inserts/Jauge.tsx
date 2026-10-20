import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import {apparition, progression} from '../anim';
import {alpha, Couleurs} from '../theme';

// 5. Jauge ou chiffre : un chiffre qui monte, avec une barre qui se remplit.
export const Jauge: React.FC<{
	valeur: number;
	unite?: string;
	libelle?: string;
	max?: number;
	barre?: boolean;
	couleurs: Couleurs;
}> = ({valeur, unite = '', libelle, max, barre, couleurs}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const p = progression(frame, Math.round(0.3 * fps), Math.round(1.4 * fps));
	const pourcent = unite.trim() === '%';
	const avecBarre = barre ?? (pourcent || max !== undefined);
	const plafond = max ?? (pourcent ? 100 : valeur);
	const decimales = Number.isInteger(valeur) ? 0 : 1;
	const affiche = (valeur * p).toLocaleString('fr-FR', {minimumFractionDigits: decimales, maximumFractionDigits: decimales});
	return (
		<div style={{display: 'flex', flexDirection: 'column', gap: 18}}>
			{libelle ? (
				<div style={{fontWeight: 600, fontSize: 40, color: alpha(couleurs.blanc, 0.8), ...apparition(frame, 4, 10)}}>
					{libelle}
				</div>
			) : null}
			<div style={{display: 'flex', alignItems: 'baseline', gap: 10, ...apparition(frame, 6, 10)}}>
				<span style={{fontWeight: 800, fontSize: 200, lineHeight: 1, letterSpacing: -4, fontVariantNumeric: 'tabular-nums'}}>
					{affiche}
				</span>
				{unite ? <span style={{fontWeight: 800, fontSize: 100, color: couleurs.bleu}}>{unite}</span> : null}
			</div>
			{avecBarre ? (
				<div style={{height: 30, borderRadius: 15, background: alpha(couleurs.blanc, 0.1), overflow: 'hidden', marginTop: 8}}>
					<div
						style={{
							height: '100%',
							borderRadius: 12,
							width: `${Math.min(100, (100 * valeur * p) / Math.max(1e-6, plafond))}%`,
							background: `linear-gradient(90deg, ${alpha(couleurs.bleu, 0.75)}, ${couleurs.bleu})`,
							boxShadow: `0 0 24px ${alpha(couleurs.bleu, 0.55)}`,
						}}
					/>
				</div>
			) : null}
		</div>
	);
};
