import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { clsx } from 'clsx';
import type { ButtonHTMLAttributes } from 'react';
import { twMerge } from 'tailwind-merge';

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 rounded-xl text-sm font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-blue-600',
  {
    variants: {
      variant: {
        default: 'button-primary px-5 py-3',
        outline: 'button-outline px-4 py-2.5',
        ghost: 'button-ghost px-3 py-2',
        destructive: 'button-destructive px-4 py-2.5',
      },
    },
    defaultVariants: { variant: 'default' },
  },
);
interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}
export function Button({ className, variant, asChild = false, ...props }: ButtonProps) {
  const Component = asChild ? Slot : 'button';
  return <Component className={twMerge(clsx(buttonVariants({ variant }), className))} {...props} />;
}
