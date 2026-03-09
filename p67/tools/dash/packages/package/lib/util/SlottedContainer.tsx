import type { SlotProps } from '@radix-ui/react-slot';
import { Slot } from '@radix-ui/react-slot';
import type {
    AnchorHTMLAttributes,
    BlockquoteHTMLAttributes,
    ButtonHTMLAttributes,
    ComponentType,
    DetailedHTMLFactory,
    DetailsHTMLAttributes,
    FormHTMLAttributes,
    ForwardedRef,
    HTMLAttributes,
    InputHTMLAttributes,
    LabelHTMLAttributes,
    LiHTMLAttributes,
    MenuHTMLAttributes,
    MeterHTMLAttributes,
    OlHTMLAttributes,
    OptgroupHTMLAttributes,
    OptionHTMLAttributes,
    OutputHTMLAttributes,
    ProgressHTMLAttributes,
    QuoteHTMLAttributes,
    ReactHTML,
    SelectHTMLAttributes,
    SVGAttributes,
    TimeHTMLAttributes,
} from 'react';
import { forwardRef } from 'react';
import { useMergedStyles } from '../hooks';
import type { StylexProps } from './StylexProps';

type ElementFromFactory<
    T extends DetailedHTMLFactory<HTMLAttributes<unknown>, HTMLElement>,
> =
    T extends DetailedHTMLFactory<HTMLAttributes<never>, infer E>
        ? E
        : HTMLElement;

interface SlottedSvgProps extends SVGAttributes<SVGElement> {
    /**
     * When this property is set to true, Stellar will not render a default DOM element,
     * instead cloning the part's child and passing it the props and behavior required to make it functional.
     *
     * This will break props that only work on specific HTML tags since Stellar delegates to the browser for all
     * default behaviors of HTML tags.
     */
    asChild?: boolean | undefined;
    /**
     * The children of the svg.
     */
    children: React.ReactNode;
}
/**
 * extensible base for components
 */
interface SlottedContainerProps<T extends keyof ReactHTML>
    extends HTMLAttributes<ElementFromFactory<ReactHTML[T]>> {
    /**
     * When this property is set to true, Stellar will not render a default DOM element,
     * instead cloning the part's child and passing it the props and behavior required to make it functional.
     *
     * This will break props that only work on specific HTML tags since Stellar delegates to the browser for all
     * default behaviors of HTML tags.
     */
    asChild?: boolean | undefined;
    /**
     * The children of the component.
     */
    children?: React.ReactNode | undefined;
}

interface SlottedAnchorContainerProps
    extends AnchorHTMLAttributes<HTMLAnchorElement>,
        SlottedContainerProps<'a'> {}

interface SlottedDivContainerProps
    extends HTMLAttributes<HTMLDivElement>,
        SlottedContainerProps<'div'> {}

interface SlottedBlockquoteContainerProps
    extends BlockquoteHTMLAttributes<HTMLQuoteElement>,
        SlottedContainerProps<'blockquote'> {}
interface SlottedButtonContainerProps
    extends ButtonHTMLAttributes<HTMLButtonElement>,
        SlottedContainerProps<'button'> {}
interface SlottedFieldsetContainerProps
    extends DetailsHTMLAttributes<HTMLFieldSetElement>,
        SlottedContainerProps<'fieldset'> {}

interface SlottedFormContainerProps
    extends FormHTMLAttributes<HTMLFormElement>,
        SlottedContainerProps<'form'> {}

interface SlottedInputContainerProps
    extends InputHTMLAttributes<HTMLInputElement>,
        // TODO: look at why this element is different
        Pick<SlottedContainerProps<'input'>, 'asChild' | 'children'> {}

interface SlottedLabelContainerProps
    extends LabelHTMLAttributes<HTMLLabelElement>,
        SlottedContainerProps<'label'> {}

interface SlottedLiContainerProps
    extends LiHTMLAttributes<HTMLLIElement>,
        SlottedContainerProps<'li'> {}
interface SlottedMenuContainerProps
    extends MenuHTMLAttributes<HTMLElement>,
        SlottedContainerProps<'menu'> {}
interface SlottedMeterContainerProps
    extends MeterHTMLAttributes<HTMLMeterElement>,
        SlottedContainerProps<'meter'> {}
interface SlottedOlContainerProps
    extends OlHTMLAttributes<HTMLOListElement>,
        SlottedContainerProps<'ol'> {}
interface SlottedOptGroupContainerProps
    extends OptgroupHTMLAttributes<HTMLOptGroupElement>,
        SlottedContainerProps<'optgroup'> {}
interface SlottedOptionContainerProps
    extends OptionHTMLAttributes<HTMLOptionElement>,
        SlottedContainerProps<'option'> {}
interface SlottedOutputContainerProps
    extends OutputHTMLAttributes<HTMLOutputElement>,
        SlottedContainerProps<'output'> {}

interface SlottedProgressContainerProps
    extends ProgressHTMLAttributes<HTMLProgressElement>,
        SlottedContainerProps<'progress'> {}

interface SlottedQuoteContainerProps
    extends QuoteHTMLAttributes<HTMLQuoteElement>,
        SlottedContainerProps<'q'> {}
interface SlottedSelectContainerProps
    extends SelectHTMLAttributes<HTMLSelectElement>,
        Pick<SlottedContainerProps<'select'>, 'asChild' | 'children'> {}

interface SlottedTimeContainerProps
    extends TimeHTMLAttributes<HTMLTimeElement>,
        SlottedContainerProps<'time'> {}
/*
Remaning tags that have different attributes that we don't expect to use in Stellar yet.

Please add to list of interfaces here if any of these becomes needed for your usecase.

        area: DetailedHTMLFactory<AreaHTMLAttributes<HTMLAreaElement>, HTMLAreaElement>;
        audio: DetailedHTMLFactory<AudioHTMLAttributes<HTMLAudioElement>, HTMLAudioElement>;
        base: DetailedHTMLFactory<BaseHTMLAttributes<HTMLBaseElement>, HTMLBaseElement>;
        canvas: DetailedHTMLFactory<CanvasHTMLAttributes<HTMLCanvasElement>, HTMLCanvasElement>;
        col: DetailedHTMLFactory<ColHTMLAttributes<HTMLTableColElement>, HTMLTableColElement>;
        colgroup: DetailedHTMLFactory<ColgroupHTMLAttributes<HTMLTableColElement>, HTMLTableColElement>;
        data: DetailedHTMLFactory<DataHTMLAttributes<HTMLDataElement>, HTMLDataElement>;
        del: DetailedHTMLFactory<DelHTMLAttributes<HTMLModElement>, HTMLModElement>;
        details: DetailedHTMLFactory<DetailsHTMLAttributes<HTMLDetailsElement>, HTMLDetailsElement>;
        dialog: DetailedHTMLFactory<DialogHTMLAttributes<HTMLDialogElement>, HTMLDialogElement>;
        embed: DetailedHTMLFactory<EmbedHTMLAttributes<HTMLEmbedElement>, HTMLEmbedElement>;
        html: DetailedHTMLFactory<HtmlHTMLAttributes<HTMLHtmlElement>, HTMLHtmlElement>;
        iframe: DetailedHTMLFactory<IframeHTMLAttributes<HTMLIFrameElement>, HTMLIFrameElement>;
        img: DetailedHTMLFactory<ImgHTMLAttributes<HTMLImageElement>, HTMLImageElement>;
        ins: DetailedHTMLFactory<InsHTMLAttributes<HTMLModElement>, HTMLModElement>;
        keygen: DetailedHTMLFactory<KeygenHTMLAttributes<HTMLElement>, HTMLElement>;
        li: DetailedHTMLFactory<LiHTMLAttributes<HTMLLIElement>, HTMLLIElement>;
        link: DetailedHTMLFactory<LinkHTMLAttributes<HTMLLinkElement>, HTMLLinkElement>;
        map: DetailedHTMLFactory<MapHTMLAttributes<HTMLMapElement>, HTMLMapElement>;
        meta: DetailedHTMLFactory<MetaHTMLAttributes<HTMLMetaElement>, HTMLMetaElement>;
        object: DetailedHTMLFactory<ObjectHTMLAttributes<HTMLObjectElement>, HTMLObjectElement>;
        slot: DetailedHTMLFactory<SlotHTMLAttributes<HTMLSlotElement>, HTMLSlotElement>;
        script: DetailedHTMLFactory<ScriptHTMLAttributes<HTMLScriptElement>, HTMLScriptElement>;
        source: DetailedHTMLFactory<SourceHTMLAttributes<HTMLSourceElement>, HTMLSourceElement>;
        style: DetailedHTMLFactory<StyleHTMLAttributes<HTMLStyleElement>, HTMLStyleElement>;
        table: DetailedHTMLFactory<TableHTMLAttributes<HTMLTableElement>, HTMLTableElement>;
        td: DetailedHTMLFactory<TdHTMLAttributes<HTMLTableDataCellElement>, HTMLTableDataCellElement>;
        textarea: DetailedHTMLFactory<TextareaHTMLAttributes<HTMLTextAreaElement>, HTMLTextAreaElement>;
        th: DetailedHTMLFactory<ThHTMLAttributes<HTMLTableHeaderCellElement>, HTMLTableHeaderCellElement>;
        track: DetailedHTMLFactory<TrackHTMLAttributes<HTMLTrackElement>, HTMLTrackElement>;
        video: DetailedHTMLFactory<VideoHTMLAttributes<HTMLVideoElement>, HTMLVideoElement>;
        webview: DetailedHTMLFactory<WebViewHTMLAttributes<HTMLWebViewElement>, HTMLWebViewElement>;
    }
    */
/**
 * internal implementation adds stylex and tag props. to be specified when using SlottedComponent
 */

interface SlottedContainerInnerProps<T extends keyof ReactHTML>
    extends SlottedContainerProps<T> {
    /**
     * The tag of the component.
     */
    tag: T;
    /**
     * The stylex props of the component.
     */
    stylexProps: StylexProps;
}

/**
 * The inner component of the slotted container.
 */
function SlottedContainerInner<
    T extends SlottedContainerInnerProps<keyof ReactHTML>,
    E extends HTMLElement = HTMLElement,
>(props: T, forwardedRef: ForwardedRef<E>) {
    const {
        asChild,
        children,
        tag,
        className,
        style,
        stylexProps,
        ...otherProps
    } = props;
    const Component: ComponentType<SlotProps> | string = asChild ? Slot : tag;
    const styleProps = useMergedStyles(className, style, stylexProps);
    return (
        <Component {...otherProps} {...styleProps} ref={forwardedRef}>
            {children}
        </Component>
    );
}

const SlottedContainer = forwardRef(SlottedContainerInner);
SlottedContainer.displayName = 'SlottedContainer';

export { Slottable } from '@radix-ui/react-slot';
export { SlottedContainer };
export type {
    SlottedAnchorContainerProps,
    SlottedBlockquoteContainerProps,
    SlottedButtonContainerProps,
    SlottedContainerProps,
    SlottedDivContainerProps,
    SlottedFieldsetContainerProps,
    SlottedFormContainerProps,
    SlottedInputContainerProps,
    SlottedLabelContainerProps,
    SlottedLiContainerProps,
    SlottedMenuContainerProps,
    SlottedMeterContainerProps,
    SlottedOlContainerProps,
    SlottedOptGroupContainerProps,
    SlottedOptionContainerProps,
    SlottedOutputContainerProps,
    SlottedProgressContainerProps,
    SlottedQuoteContainerProps,
    SlottedSelectContainerProps,
    SlottedSvgProps,
    SlottedTimeContainerProps,
};
