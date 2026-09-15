import { render, fireEvent } from '@testing-library/react';
import React from 'react';
import { useUncontrolled } from '../src';

describe('uncontrollable', () => {
  it('should track internally if not specified', () => {
    let ref = {};
    let Control = (props) => {
      props = useUncontrolled(props, { value: 'onChange' });
      ref.current = props;

      return (
        <input
          {...props}
          data-testid="input"
          value={props.value == null ? '' : props.value}
          onChange={(e) => props.onChange(+e.target.value)}
        />
      );
    };

    let inst = render(<Control />);

    fireEvent.change(inst.getByTestId('input'), { target: { value: 42 } });

    expect(ref.current.value).toEqual(42);
  });

  it('should allow for defaultProp', () => {
    let ref = {};
    let Control = (props) => {
      props = useUncontrolled(props, {
        value: 'onChange',
        open: 'onToggle',
      });

      ref.current = props;

      return (
        <input
          {...props}
          className={props.open ? 'open' : ''}
          data-testid="input"
          value={props.value == null ? '' : props.value}
          onChange={(e) => props.onChange(+e.target.value)}
        />
      );
    };
    let inst = render(<Control defaultValue={10} defaultOpen />);

    expect(inst.container.querySelectorAll('.open')).toHaveLength(1);

    expect(ref.current.defaultValue).not.toBeDefined();
    expect(ref.current.defaultOpen).not.toBeDefined();

    let input = inst.container.querySelector('input');

    expect(input.value).toEqual('10');

    fireEvent.change(inst.getByTestId('input'), { target: { value: 42 } });
    expect(ref.current.value).toEqual(42);
  });

  it('should revert to defaultProp when switched to uncontrolled', () => {
    let ref = {};
    let Control = (props) => {
      props = useUncontrolled(props, { value: 'onChange' });
      ref.current = props;

      return (
        <input
          {...props}
          data-testid="input"
          value={props.value == null ? '' : props.value}
          onChange={(e) => props.onChange(e.value)}
        />
      );
    };

    let inst = render(
      <Control defaultValue="foo" value="bar" onChange={() => {}} />
    );

    expect(ref.current.value).toEqual('bar');

    inst.rerender(<Control defaultValue="foo" onChange={() => {}} />);

    expect(ref.current.value).toEqual('foo');

    inst.rerender(
      <Control defaultValue="foo" value="bar" onChange={() => {}} />
    );

    expect(ref.current.value).toEqual('bar');

    inst.rerender(
      <Control defaultValue="baz" value={undefined} onChange={() => {}} />
    );

    expect(ref.current.value).toEqual('baz');
  });
});
