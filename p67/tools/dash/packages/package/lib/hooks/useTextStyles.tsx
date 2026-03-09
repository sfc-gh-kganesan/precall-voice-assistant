import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import type {
    CompiledStyles,
    InlineStyles,
    StyleXArray,
    StyleXClassNameFor,
} from '@stylexjs/stylex';
import * as stylex from '@stylexjs/stylex';

type TextSize =
    | 'xsmall' // 9
    | 'smallcaps' // 11
    | 'small' // 12
    | 'regularcaps' //13
    | 'regular' //14
    | 'largecaps' //15
    | 'large' //16
    | 'xlargecaps' // 19
    | 'xlarge' //20
    | 'xxlargecaps' //27
    | 'xxlarge' //28
    | 'xxxlargecaps' //39
    | 'xxxlarge'; //40

type TextWeight = 'regular' | 'medium' | 'semibold' | 'bold';

interface TextSizeAndWeight {
    /**
     * The size of the text.
     */
    size?: TextSize | undefined;
    /**
     * The weight of the text.
     */
    weight?: TextWeight | undefined;
}

const textSize = stylex.create({
    font: {
        fontFamily: baltoTheme.fontFamilyBody,
    },

    text: {
        margin: 0,
        padding: 0,
    },
    xSmall: {
        fontSize: `calc(${baltoTheme.fontSizeSmall} - 3px)`,
    },
    smallCaps: {
        fontSize: `calc(${baltoTheme.fontSizeSmall} - 1px)`,
        textTransform: 'uppercase',
    },
    small: {
        fontSize: baltoTheme.fontSizeSmall,
    },
    regularCaps: {
        fontSize: `calc(${baltoTheme.fontSizeRegular} - 1px)`,
        textTransform: 'uppercase',
    },
    regular: {
        fontSize: baltoTheme.fontSizeRegular,
    },
    largeCaps: {
        fontSize: `calc(${baltoTheme.fontSizeLarge} - 1px)`,
        textTransform: 'uppercase',
    },
    large: {
        fontSize: baltoTheme.fontSizeLarge,
    },
    xLargeCaps: {
        fontSize: `calc(${baltoTheme.fontSizeXlarge} - 1px)`,
        textTransform: 'uppercase',
    },
    xLarge: {
        fontSize: baltoTheme.fontSizeXlarge,
    },

    xxLargeCaps: {
        fontSize: `calc(${baltoTheme.fontSizeXxlarge} - 1px)`,
        textTransform: 'uppercase',
    },
    xxLarge: {
        fontSize: baltoTheme.fontSizeXxlarge,
    },
    xxxLargeCaps: {
        fontSize: `calc(${baltoTheme.fontSizeXxxlarge} - 1px)`,
        textTransform: 'uppercase',
    },
    xxxLarge: {
        fontSize: baltoTheme.fontSizeXxxlarge,
    },
    weightBold: {
        fontWeight: baltoTheme.fontWeightBold,
    },
    weightSemiBold: {
        fontWeight: baltoTheme.fontWeightSemiBold,
    },
    weightMedium: {
        fontWeight: baltoTheme.fontWeightMedium,
    },
    weightRegular: {
        fontWeight: baltoTheme.fontWeightRegular,
    },
});

type FontSizeAndCaseStyle = Readonly<{
    /**
     * The size of the text.
     */
    readonly fontSize: StyleXClassNameFor<'fontSize', string>;
    /**
     * The case of the text.
     */
    readonly textTransform?:
        | StyleXClassNameFor<'textTransform', 'uppercase'>
        | undefined;
}>;
const textSizeStyles: Readonly<Record<TextSize, FontSizeAndCaseStyle>> = {
    xsmall: textSize.xSmall,
    smallcaps: textSize.smallCaps,
    small: textSize.small,
    regularcaps: textSize.regularCaps,
    regular: textSize.regular,
    largecaps: textSize.largeCaps,
    large: textSize.large,
    xlargecaps: textSize.xLargeCaps,
    xlarge: textSize.xLarge,
    xxlargecaps: textSize.xxLargeCaps,
    xxlarge: textSize.xxLarge,
    xxxlargecaps: textSize.xxxLargeCaps,
    xxxlarge: textSize.xxxLarge,
} as const;

type FontWeightStyle = Readonly<{
    /**
     * The weight of the text.
     */
    readonly fontWeight: StyleXClassNameFor<'fontWeight', number>;
}>;
const textWeightStyles: Readonly<Record<TextWeight, FontWeightStyle>> = {
    regular: textSize.weightRegular,
    medium: textSize.weightMedium,
    bold: textSize.weightBold,
    semibold: textSize.weightSemiBold,
} as const;

const useTextStyles = (
    props: TextSizeAndWeight = {},
): ReadonlyArray<
    StyleXArray<
        | (null | undefined | CompiledStyles)
        | boolean
        | Readonly<[CompiledStyles, InlineStyles]>
    >
> => {
    const { size = 'regular', weight = 'regular' } = props;
    return [textSize.font, textSizeStyles[size], textWeightStyles[weight]];
};

export type { TextSize, TextWeight, TextSizeAndWeight };
export { useTextStyles, textSizeStyles, textWeightStyles };
