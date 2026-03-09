import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import * as stylex from '@stylexjs/stylex';

const styles = stylex.create({
    smallParagraph: {
        fontFamily: baltoTheme.fontFamilyBody,
        fontSize: baltoTheme.fontSizeSmall,
        fontWeight: baltoTheme.fontWeightRegular,
        lineHeight: baltoTheme.lineHeightSmallBody,
    },

    smallParagraphBold: {
        fontFamily: baltoTheme.fontFamilyBody,
        fontSize: baltoTheme.fontSizeSmall,
        fontWeight: baltoTheme.fontWeightSemiBold,
        lineHeight: baltoTheme.lineHeightSmallBody,
    },

    smallSingleLine: {
        fontFamily: baltoTheme.fontFamilyBody,
        fontSize: baltoTheme.fontSizeSmall,
        fontWeight: baltoTheme.fontWeightRegular,
        lineHeight: baltoTheme.lineHeightSmallSingleLine,
    },

    smallSingleLineBold: {
        fontFamily: baltoTheme.fontFamilyBody,
        fontSize: baltoTheme.fontSizeSmall,
        fontWeight: baltoTheme.fontWeightSemiBold,
        lineHeight: baltoTheme.lineHeightSmallSingleLine,
    },

    labelSmall: {
        fontFamily: baltoTheme.fontFamilyBody,
        fontSize: baltoTheme.fontSizeSmall,
        fontWeight: baltoTheme.fontWeightMedium,
        // rename these to use non-semantic line-height tokens
        lineHeight: baltoTheme.lineHeightRegularSingleLine,
    },

    label: {
        fontFamily: baltoTheme.fontFamilyBody,
        fontSize: baltoTheme.fontSizeRegular,
        fontWeight: baltoTheme.fontWeightMedium,
        // rename these to use non-semantic line-height tokens
        lineHeight: baltoTheme.lineHeightRegularSingleLine,
    },

    regularSingleLine: {
        fontFamily: baltoTheme.fontFamilyBody,
        fontSize: baltoTheme.fontSizeRegular,
        fontWeight: baltoTheme.fontWeightRegular,
        lineHeight: baltoTheme.lineHeightRegularSingleLine,
    },

    boldSingleLine: {
        fontFamily: baltoTheme.fontFamilyBody,
        fontSize: baltoTheme.fontSizeRegular,
        fontWeight: baltoTheme.fontWeightSemiBold,
        lineHeight: baltoTheme.lineHeightRegularSingleLine,
    },

    paragraph: {
        fontFamily: baltoTheme.fontFamilyBody,
        fontSize: baltoTheme.fontSizeRegular,
        fontWeight: baltoTheme.fontWeightRegular,
        lineHeight: baltoTheme.lineHeightRegularBody,
    },

    boldParagraph: {
        fontFamily: baltoTheme.fontFamilyBody,
        fontSize: baltoTheme.fontSizeRegular,
        fontWeight: baltoTheme.fontWeightSemiBold,
        lineHeight: baltoTheme.lineHeightRegularBody,
    },

    error: {
        fontFamily: baltoTheme.fontFamilyBody,
        fontSize: baltoTheme.fontSizeSmall,
        fontWeight: baltoTheme.fontWeightRegular,
        lineHeight: baltoTheme.lineHeightRegularSingleLine,
    },

    link: {
        fontFamily: baltoTheme.fontFamilyBody,
        fontSize: baltoTheme.fontSizeRegular,
        fontWeight: baltoTheme.fontWeightRegular,
        lineHeight: baltoTheme.lineHeightRegularSingleLine,
    },

    subHeader: {
        fontFamily: baltoTheme.fontFamilyHeading,
        fontSize: baltoTheme.fontSizeLarge,
        fontWeight: baltoTheme.fontWeightSemiBold,
        lineHeight: baltoTheme.lineHeightSubHeader,
    },

    pageHeader: {
        fontFamily: baltoTheme.fontFamilyHeading,
        fontSize: baltoTheme.fontSizeXlarge,
        fontWeight: baltoTheme.fontWeightBold,
        lineHeight: baltoTheme.lineHeightPageHeader,
    },

    largeEditorialHeadline: {
        fontFamily: baltoTheme.fontFamilyEditorial,
        fontSize: baltoTheme.fontSizeXxlarge,
        fontWeight: baltoTheme.fontWeightBold,
        lineHeight: baltoTheme.lineHeightLargeEditorial,
    },

    largerEditorialHeadline: {
        fontFamily: baltoTheme.fontFamilyEditorial,
        fontSize: baltoTheme.fontSizeXxxlarge,
        fontWeight: baltoTheme.fontWeightBold,
        lineHeight: baltoTheme.lineHeightLargerEditorial,
    },

    allCapsSmall: {
        fontFamily: baltoTheme.fontFamilyBody,
        fontSize: `calc(${baltoTheme.fontSizeSmall} - 1px)`,
        fontWeight: baltoTheme.fontWeightMedium,
        lineHeight: baltoTheme.lineHeightRegularSingleLine,
        textTransform: 'uppercase',
    },

    allCaps: {
        fontFamily: baltoTheme.fontFamilyBody,
        fontSize: `calc(${baltoTheme.fontSizeRegular} - 1px)`,
        fontWeight: baltoTheme.fontWeightMedium,
        lineHeight: baltoTheme.lineHeightRegularBody,
        textTransform: 'uppercase',
    },
});

type TypeName = keyof typeof styles;

export function useTypeRamp(name: TypeName) {
    return styles[name];
}

export function getTypeRamp(name: TypeName) {
    return styles[name];
}
