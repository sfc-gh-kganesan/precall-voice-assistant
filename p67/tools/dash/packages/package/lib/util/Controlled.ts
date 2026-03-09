/**
 * Utility type that capitalizes the first letter of a string type.
 * @template T - The input string type to transform
 */
type CapitalFirst<T extends string> = string extends T
    ? string
    : T extends `${infer C0}${infer R}`
      ? `${Uppercase<C0>}${R}`
      : T;

/**
 * Creates a union type of controlled component field tuples.
 * Each tuple contains a field name and its corresponding value type.
 * @template T - The base field name
 * @template V - The value type
 * @template C - Optional context type for change handlers
 */
type Fields<T extends string, V, C = never> =
    | [`${T}`, V]
    | [`default${CapitalFirst<T>}`, V]
    | [`on${CapitalFirst<T>}Change`, (value: V, ctx?: C | undefined) => void];

/**
 * Creates a type for a controlled component with specified field name, value type, and optional context.
 * Includes properties for current value, default value, and change handler.
 * @template T - The base field name
 * @template V - The value type
 * @template C - Optional context type for change handlers
 */
export type ControlledComponent<T extends string, V, C = never> = {
    [F in Fields<T, V, C> as F[0]]?: F[1] | undefined;
};

/**
 * A specialized controlled component type for components with a "value" property.
 * @template V - The type of the value
 */
export type ControlledValueComponent<V> = ControlledComponent<'value', V>;

/**
 * A specialized controlled component type for components with an "open" boolean property.
 */
export type ControlledOpenComponent = ControlledComponent<'open', boolean>;
