export declare const ATTRIBUTE_PREFIX: "data-rr-ui-";
export declare const PROPERTY_PREFIX: "rrUi";
export declare function dataAttr<T extends string>(property: T): `data-rr-ui-${T}`;
export declare function dataProp<T extends string>(property: T): `rrUi${T}`;
