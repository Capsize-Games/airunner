import { useUncontrolled, useUncontrolledProp } from '../src';

interface Props {
  value?: string;
  defaultValue: string | undefined;
  onChange?(value: string, meta: {}): void;
}

function Foo(props: Props) {
  // $ExpectType [string, (value: string, meta: {}) => void]
  const [value, onChange] = useUncontrolledProp(
    props.value,
    props.defaultValue,
    props.onChange
  );
}

interface Props2 {
  value?: string;
  defaultValue: string | undefined;
  onChange?(value: string, meta: {}): Promise<void>;
}

function Foo2(props: Props2) {
  // $ExpectType [string, (value: string, meta: {}) => void | Promise<void>]
  const [value, onChange] = useUncontrolledProp(
    props.value,
    props.defaultValue,
    props.onChange
  );
}

function FooA(props: Props) {
  // $ExpectType { value: string, onChange:  (value: string, meta: {}) => void }
  const a = useUncontrolled<Props, 'defaultValue'>(props, {
    value: 'onChange',
  });

  // $ExpectType Props
  const b = useUncontrolled(props, {
    value: 'onChange',
  });
}
