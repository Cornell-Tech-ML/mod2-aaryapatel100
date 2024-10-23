"""Implementation of the autodifferentiation Functions for Tensor."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

import numpy as np

import minitorch

from . import operators
from .autodiff import Context
from .tensor_ops import SimpleBackend, TensorBackend

if TYPE_CHECKING:
    from typing import Any, List, Tuple

    from .tensor import Tensor
    from .tensor_data import UserIndex, UserShape


def wrap_tuple(x: Any) -> tuple:  # type: ignore
    """Turn a possible value into a tuple"""
    if isinstance(x, tuple):
        return x
    return (x,)


# Constructors
class Function:
    @classmethod
    def _backward(cls, ctx: Context, grad_out: Tensor) -> Tuple[Tensor, ...]:
        return wrap_tuple(cls.backward(ctx, grad_out))  # type: ignore

    @classmethod
    def _forward(cls, ctx: Context, *inps: Tensor) -> Tensor:
        return cls.forward(ctx, *inps)  # type: ignore

    @classmethod
    def apply(cls, *vals: Tensor) -> Tensor:
        """Call the forward function and track history"""
        raw_vals = []
        need_grad = False
        for v in vals:
            if v.requires_grad():
                need_grad = True
            raw_vals.append(v.detach())

        # Create the context.
        ctx = Context(not need_grad)

        # Call forward with the variables.
        c = cls._forward(ctx, *raw_vals)
        # assert isinstance(c, Tensor), "Expected return type Tensor got %s" % (
        #     type(c)
        # )

        # Create a new variable from the result with a new history.
        back = None
        if need_grad:
            back = minitorch.History(cls, ctx, vals)
        return minitorch.Tensor(c._tensor, back, backend=c.backend)


class Neg(Function):
    @staticmethod
    def forward(ctx: Context, t1: Tensor) -> Tensor:
        """Performs the forward pass of the negation operation.

        Args:
        ----
            ctx (Context): The context to store information for backward computation.
            t1 (Tensor): The input tensor to be negated.

        Returns:
        -------
            Tensor: A tensor where each element is the negation of the input tensor.

        """
        return t1.f.neg_map(t1)

    @staticmethod
    def backward(ctx: Context, grad_output: Tensor) -> Tensor:
        """Computes the gradient of the negation function during the backward pass.

        Args:
        ----
            ctx (Context): The context storing information from the forward pass.
            grad_output (Tensor): The derivative of the loss with respect to the output.

        Returns:
        -------
            Tensor: The gradient with respect to the input `a`.

        """
        return grad_output.f.neg_map(grad_output)


class Inv(Function):
    @staticmethod
    def forward(ctx: Context, t1: Tensor) -> Tensor:
        """Computes the element-wise inverse of the input tensor.

        Args:
        ----
            ctx (Context): The context storing information from the forward pass.
            t1 (Tensor): The input tensor to be inverted.

        Returns:
        -------
            Tensor: A tensor where each element is the inverse of the input tensor.

        """
        ctx.save_for_backward(t1)
        return t1.f.inv_map(t1)

    @staticmethod
    def backward(ctx: Context, grad_output: Tensor) -> Tensor:
        """Computes the gradient of the inverse function during the backward pass.

        Args:
        ----
            ctx (Context): The context storing information from the forward pass.
            grad_output (Tensor): The derivative of the loss with respect to the output.

        Returns:
        -------
            Tensor: The gradient with respect to the input `t1`.

        """
        (t1,) = ctx.saved_values
        return grad_output.f.inv_back_zip(t1, grad_output)


class Add(Function):
    @staticmethod
    def forward(ctx: Context, t1: Tensor, t2: Tensor) -> Tensor:
        """Computes the element-wise addition of two tensors.

        Args:
        ----
            ctx (Context): The context storing information from the forward pass.
            t1 (Tensor): The first input tensor.
            t2 (Tensor): The second input tensor.

        Returns:
        -------
            Tensor: A tensor where each element is the addition of the corresponding elements in `t1` and `t2`.

        """
        return t1.f.add_zip(t1, t2)

    @staticmethod
    def backward(ctx: Context, grad_output: Tensor) -> Tuple[Tensor, Tensor]:
        """Computes the gradient of the addition function during the backward pass.

        Args:
        ----
            ctx (Context): The context storing information from the forward pass.
            grad_output (Tensor): The derivative of the loss with respect to the output.

        Returns:
        -------
            Tuple[Tensor, Tensor]: A tuple of two tensors, each of which is the gradient with respect to the input `t1` and `t2` respectively.

        """
        return grad_output, grad_output


class All(Function):
    @staticmethod
    def forward(ctx: Context, a: Tensor, dim: Tensor) -> Tensor:
        """Return 1 if all are true"""
        if dim is not None:
            return a.f.mul_reduce(a, int(dim.item()))
        else:
            return a.f.mul_reduce(a.contiguous().view(int(operators.prod(a.shape))), 0)


class Mul(Function):
    @staticmethod
    def forward(ctx: Context, t1: Tensor, t2: Tensor) -> Tensor:
        """Computes the element-wise multiplication of two tensors.

        Args:
        ----
            ctx (Context): The context storing information from the forward pass.
            t1 (Tensor): The first input tensor.
            t2 (Tensor): The second input tensor.

        Returns:
        -------
            Tensor: A tensor where each element is the multiplication of the corresponding elements in `t1` and `t2`.

        """
        ctx.save_for_backward(t1, t2)
        return t1.f.mul_zip(t1, t2)

    @staticmethod
    def backward(ctx: Context, grad_output: Tensor) -> Tuple[Tensor, Tensor]:
        """Computes the gradient of the multiplication function during the backward pass.

        Args:
        ----
            ctx (Context): The context storing information from the forward pass.
            grad_output (Tensor): The derivative of the loss with respect to the output.

        Returns:
        -------
            Tuple[Tensor, Tensor]: A tuple of two tensors, each of which is the gradient with respect to the input `t1` and `t2` respectively.

        """
        t1, t2 = ctx.saved_values
        return grad_output.f.mul_zip(grad_output, t2), grad_output.f.mul_zip(
            grad_output, t1
        )


class Sigmoid(Function):
    @staticmethod
    def forward(ctx: Context, t1: Tensor) -> Tensor:
        """Performs the forward pass of the sigmoid function on a tensor.

        Args:
        ----
            ctx (Context): The context to store information for backward computation.
            t1 (Tensor): The input tensor for which to apply the sigmoid function.

        Returns:
        -------
            Tensor: A tensor where each element is the result of applying the sigmoid function to the corresponding element of the input tensor.

        """
        output = t1.f.sigmoid_map(t1)
        ctx.save_for_backward(output)
        return output

    @staticmethod
    def backward(ctx: Context, grad_output: Tensor) -> Tuple[Tensor]:
        """Computes the gradient of the sigmoid function during the backward pass.

        Args:
        ----
            ctx (Context): The context storing information from the forward pass.
            grad_output (Tensor): The derivative of the loss with respect to the output.

        Returns:
        -------
            Tuple[Tensor]: A tuple of a single tensor, which is the gradient with respect to the input `t1`.

        """
        (output,) = ctx.saved_values
        sig_grad = grad_output.f.mul_zip(
            output,
            grad_output.f.add_zip(tensor([1]), grad_output.f.neg_map(output)),
        )
        return (grad_output.f.mul_zip(grad_output, sig_grad),)


class ReLU(Function):
    @staticmethod
    def forward(ctx: Context, t1: Tensor) -> Tensor:
        """Performs the forward pass of the ReLU function on a tensor.

        Args:
        ----
            ctx (Context): The context to store information for backward computation.
            t1 (Tensor): The input tensor for which to apply the ReLU function.

        Returns:
        -------
            Tensor: A tensor where each element is the result of applying the ReLU function to the corresponding element of the input tensor.

        """
        ctx.save_for_backward(t1)
        return t1.f.relu_map(t1)

    @staticmethod
    def backward(ctx: Context, grad_output: Tensor) -> Tensor:
        """Computes the gradient of the ReLU function during the backward pass.

        Args:
        ----
            ctx (Context): The context storing information from the forward pass.
            grad_output (Tensor): The derivative of the loss with respect to the output.

        Returns:
        -------
            Tensor: The gradient with respect to the input `t1`.

        """
        (t1,) = ctx.saved_values
        return grad_output.f.relu_back_zip(t1, grad_output)


class Log(Function):
    @staticmethod
    def forward(ctx: Context, t1: Tensor) -> Tensor:
        """Performs the forward pass of the natural logarithm function on a tensor.

        Args:
        ----
            ctx (Context): The context to store information for backward computation.
            t1 (Tensor): The input tensor for which to apply the natural logarithm function.

        Returns:
        -------
            Tensor: A tensor where each element is the result of applying the natural logarithm function to the corresponding element of the input tensor.

        """
        ctx.save_for_backward(t1)
        return t1.f.log_map(t1)

    @staticmethod
    def backward(ctx: Context, grad_output: Tensor) -> Tensor:
        """Computes the gradient of the natural logarithm function during the backward pass.

        Args:
        ----
            ctx (Context): The context storing information from the forward pass.
            grad_output (Tensor): The derivative of the loss with respect to the output.

        Returns:
        -------
            Tensor: The gradient with respect to the input `t1`.

        """
        (t1,) = ctx.saved_values
        return grad_output.f.log_back_zip(t1, grad_output)


class Exp(Function):
    @staticmethod
    def forward(ctx: Context, t1: Tensor) -> Tensor:
        """Performs the forward pass of the exponential function on a tensor.

        Args:
        ----
            ctx (Context): The context to store information for backward computation.
            t1 (Tensor): The input tensor for which to apply the exponential function.

        Returns:
        -------
            Tensor: A tensor where each element is the result of applying the exponential function to the corresponding element of the input tensor.

        """
        output = t1.f.exp_map(t1)
        ctx.save_for_backward(output)
        return output

    @staticmethod
    def backward(ctx: Context, grad_output: Tensor) -> Tensor:
        """Computes the gradient of the exponential function during the backward pass.

        Args:
        ----
            ctx (Context): The context storing information from the forward pass.
            grad_output (Tensor): The derivative of the loss with respect to the output.

        Returns:
        -------
            Tensor: The gradient with respect to the input `t1`.

        """
        (output,) = ctx.saved_values
        return grad_output.f.mul_zip(grad_output, output)


class Sum(Function):
    @staticmethod
    def forward(ctx: Context, t1: Tensor, dim: Tensor) -> Tensor:
        """Performs the forward pass of the sum function on a tensor.

        Args:
        ----
            ctx (Context): The context to store information for backward computation.
            t1 (Tensor): The input tensor for which to apply the sum function.
            dim (Tensor): The dimension along which to sum.

        Returns:
        -------
            Tensor: A tensor containing the sum of the input tensor along the specified dimension.

        """
        ctx.save_for_backward(t1.shape, None)
        return t1.f.add_reduce(t1, int(dim.item()))

    @staticmethod
    def backward(ctx: Context, grad_output: Tensor) -> Tuple[Tensor, float]:
        """Computes the gradient of the sum function during the backward pass.

        Args:
        ----
            ctx (Context): The context storing information from the forward pass.
            grad_output (Tensor): The derivative of the loss with respect to the output.

        Returns:
        -------
            Tuple[Tensor, float]: A tuple of two tensors, the first of which is the gradient with respect to the input `t1`, and the second of which is the gradient with respect to the input `dim`.

        """
        shape1, dim = ctx.saved_values
        return grad_output, 0.0


class LT(Function):
    @staticmethod
    def forward(ctx: Context, t1: Tensor, t2: Tensor) -> Tensor:
        """Performs the forward pass of the less than function on two tensors.

        Args:
        ----
            ctx (Context): The context to store information for backward computation.
            t1 (Tensor): The first input tensor.
            t2 (Tensor): The second input tensor.

        Returns:
        -------
            Tensor: A tensor where each element is 1 if the corresponding elements in `t1` and `t2` satisfy the condition, and 0 otherwise.

        """
        ctx.save_for_backward(t1.shape, t2.shape)
        return t1.f.lt_zip(t1, t2)

    @staticmethod
    def backward(ctx: Context, grad_output: Tensor) -> Tuple[Tensor, Tensor]:
        """Computes the gradient of the less than function during the backward pass.

        Args:
        ----
            ctx (Context): The context storing information from the forward pass.
            grad_output (Tensor): The derivative of the loss with respect to the output.

        Returns:
        -------
            Tuple[Tensor, Tensor]: A tuple of two tensors, the first of which is the gradient with respect to the input `t1`, and the second of which is the gradient with respect to the input `t2`.

        """
        shape1, shape2 = ctx.saved_values
        return grad_output.zeros(shape1), grad_output.zeros(shape2)


class EQ(Function):
    @staticmethod
    def forward(ctx: Context, t1: Tensor, t2: Tensor) -> Tensor:
        """Performs the forward pass of the equality function on two tensors.

        Args:
        ----
            ctx (Context): The context to store information for backward computation.
            t1 (Tensor): The first input tensor.
            t2 (Tensor): The second input tensor.

        Returns:
        -------
            Tensor: A tensor where each element is 1 if the corresponding elements in `t1` and `t2` are equal, and 0 otherwise.

        """
        ctx.save_for_backward(t1.shape, t2.shape)
        return t1.f.eq_zip(t1, t2)

    @staticmethod
    def backward(ctx: Context, grad_output: Tensor) -> Tuple[Tensor, Tensor]:
        """Computes the gradient of the equality function during the backward pass.

        Args:
        ----
            ctx (Context): The context storing information from the forward pass.
            grad_output (Tensor): The derivative of the loss with respect to the output.

        Returns:
        -------
            Tuple[Tensor, Tensor]: A tuple of two tensors, the first of which is the gradient with respect to the input `t1`, and the second of which is the gradient with respect to the input `t2`.

        """
        shape1, shape2 = ctx.saved_values
        return grad_output.zeros(shape1), grad_output.zeros(shape2)


class IsClose(Function):
    @staticmethod
    def forward(ctx: Context, t1: Tensor, t2: Tensor) -> Tensor:
        """Performs the forward pass of the is close function on two tensors.

        Args:
        ----
            ctx (Context): The context to store information for backward computation.
            t1 (Tensor): The first input tensor.
            t2 (Tensor): The second input tensor.

        Returns:
        -------
            Tensor: A tensor where each element is 1 if the corresponding elements in `t1` and `t2` are close, and 0 otherwise.

        """
        return t1.f.is_close_zip(t1, t2)


class Permute(Function):
    @staticmethod
    def forward(ctx: Context, t1: Tensor, order: Tensor) -> Tensor:
        """Performs the forward pass of the permute function on a tensor.

        Args:
        ----
            ctx (Context): The context to store information for backward computation.
            t1 (Tensor): The input tensor to permute.
            order (Tensor): A tensor representing the new order of dimensions.

        Returns:
        -------
            Tensor: A new tensor with dimensions permuted as specified by `order`.

        """
        ctx.save_for_backward(t1.shape, t1._tensor.strides)
        perm = []
        for i in order._tensor.indices():
            perm.append(int(order._tensor.get(i)))
        return t1._new(t1._tensor.permute(*perm))

    @staticmethod
    def backward(ctx: Context, grad_output: Tensor) -> Tuple[Tensor, float]:
        """Computes the gradient of the permute function during the backward pass.

        Args:
        ----
            ctx (Context): The context storing information from the forward pass.
            grad_output (Tensor): The derivative of the loss with respect to the output.

        Returns:
        -------
            Tuple[Tensor, float]: A tuple where the first element is the gradient with respect to the input tensor `t1`, and the second element is a placeholder value `0.0`.

        """
        (shape1, strides1) = ctx.saved_values
        return (
            minitorch.Tensor.make(
                grad_output._tensor._storage,
                shape1,
                strides1,
                backend=grad_output.backend,
            ),
            0.0,
        )


class View(Function):
    @staticmethod
    def forward(ctx: Context, a: Tensor, shape: Tensor) -> Tensor:
        """Reshapes the input tensor `a` to the specified shape.

        Args:
        ----
            ctx (Context): The context storing information from the forward pass.
            a (Tensor): The input tensor to be reshaped.
            shape (Tensor): The desired shape of the output tensor as a tensor of integers.

        Returns:
        -------
            Tensor: The reshaped tensor.

        """
        ctx.save_for_backward(a.shape)
        assert a._tensor.is_contiguous(), "Must be contiguous to view"
        shape2 = [int(shape[i]) for i in range(shape.size)]
        return minitorch.Tensor.make(
            a._tensor._storage, tuple(shape2), backend=a.backend
        )

    @staticmethod
    def backward(ctx: Context, grad_output: Tensor) -> Tuple[Tensor, float]:
        """Matrix Multiply backward (module 3)"""
        (original,) = ctx.saved_values
        return (
            minitorch.Tensor.make(
                grad_output._tensor._storage, original, backend=grad_output.backend
            ),
            0.0,
        )


class Copy(Function):
    @staticmethod
    def forward(ctx: Context, a: Tensor) -> Tensor:
        """Id function makes contiguous"""
        return a.f.id_map(a)

    @staticmethod
    def backward(ctx: Context, grad_output: Tensor) -> Tensor:
        """Undo"""
        return grad_output


class MatMul(Function):
    @staticmethod
    def forward(ctx: Context, t1: Tensor, t2: Tensor) -> Tensor:
        """Matrix Multiply Forward (module 3)"""
        ctx.save_for_backward(t1, t2)
        return t1.f.matrix_multiply(t1, t2)

    @staticmethod
    def backward(ctx: Context, grad_output: Tensor) -> Tuple[Tensor, Tensor]:
        """Matrix Multiply backward (module 3)"""
        t1, t2 = ctx.saved_values

        def transpose(a: Tensor) -> Tensor:
            order = list(range(a.dims))  # type: ignore
            order[-2], order[-1] = order[-1], order[-2]
            return a._new(a._tensor.permute(*order))

        return (
            grad_output.f.matrix_multiply(grad_output, transpose(t2)),
            grad_output.f.matrix_multiply(transpose(t1), grad_output),
        )


# Helpers for Constructing tensors
def zeros(shape: UserShape, backend: TensorBackend = SimpleBackend) -> Tensor:
    """Produce a zero tensor of size `shape`.

    Args:
    ----
        shape : shape of tensor
        backend : tensor backend

    Returns:
    -------
        new tensor

    """
    return minitorch.Tensor.make(
        [0.0] * int(operators.prod(shape)), shape, backend=backend
    )


def rand(
    shape: UserShape,
    backend: TensorBackend = SimpleBackend,
    requires_grad: bool = False,
) -> Tensor:
    """Produce a random tensor of size `shape`.

    Args:
    ----
        shape : shape of tensor
        backend : tensor backend
        requires_grad : turn on autodifferentiation

    Returns:
    -------
        :class:`Tensor` : new tensor

    """
    vals = [random.random() for _ in range(int(operators.prod(shape)))]
    tensor = minitorch.Tensor.make(vals, shape, backend=backend)
    tensor.requires_grad_(requires_grad)
    return tensor


def _tensor(
    ls: Any,
    shape: UserShape,
    backend: TensorBackend = SimpleBackend,
    requires_grad: bool = False,
) -> Tensor:
    """Produce a tensor with data ls and shape `shape`.

    Args:
    ----
        ls: data for tensor
        shape: shape of tensor
        backend: tensor backend
        requires_grad: turn on autodifferentiation

    Returns:
    -------
        new tensor

    """
    tensor = minitorch.Tensor.make(ls, shape, backend=backend)
    tensor.requires_grad_(requires_grad)
    return tensor


def tensor(
    ls: Any, backend: TensorBackend = SimpleBackend, requires_grad: bool = False
) -> Tensor:
    """Produce a tensor with data and shape from ls

    Args:
    ----
        ls: data for tensor
        backend : tensor backend
        requires_grad : turn on autodifferentiation

    Returns:
    -------
        :class:`Tensor` : new tensor

    """

    def shape(ls: Any) -> List[int]:
        if isinstance(ls, (list, tuple)):
            return [len(ls)] + shape(ls[0])
        else:
            return []

    def flatten(ls: Any) -> List[float]:
        if isinstance(ls, (list, tuple)):
            return [y for x in ls for y in flatten(x)]
        else:
            return [ls]

    cur = flatten(ls)
    shape2 = shape(ls)
    return _tensor(cur, tuple(shape2), backend=backend, requires_grad=requires_grad)


# Gradient check for tensors


def grad_central_difference(
    f: Any, *vals: Tensor, arg: int = 0, epsilon: float = 1e-6, ind: UserIndex
) -> float:
    """Compute the derivative of f at the argument indexed by `arg`
    in the direction indexed by `ind` using central difference.

    Args:
    ----
        f: function to compute derivative of
        *vals: values to use when computing f
        arg: index of the argument to compute derivative with respect to
        epsilon: step size for central difference
        ind: index of the direction to compute derivative in

    Returns:
    -------
        derivative of f with respect to the argument indexed by `arg`
        in the direction indexed by `ind`

    """
    x = vals[arg]
    up = zeros(x.shape)
    up[ind] = epsilon
    vals1 = [x if j != arg else x + up for j, x in enumerate(vals)]
    vals2 = [x if j != arg else x - up for j, x in enumerate(vals)]
    delta: Tensor = f(*vals1).sum() - f(*vals2).sum()

    return delta[0] / (2.0 * epsilon)


def grad_check(f: Any, *vals: Tensor) -> None:
    """Check whether autodiff matches central difference."""
    for x in vals:
        x.requires_grad_(True)
        x.zero_grad_()
    random.seed(10)
    out = f(*vals)
    out.sum().backward()
    err_msg = """

Gradient check error for function %s.

Input %s

Received derivative %f for argument %d and index %s,
but was expecting derivative %f from central difference.

"""

    for i, x in enumerate(vals):
        ind = x._tensor.sample()
        check = grad_central_difference(f, *vals, arg=i, ind=ind)
        assert x.grad is not None
        np.testing.assert_allclose(
            x.grad[ind],
            check,
            1e-2,
            1e-2,
            err_msg=err_msg % (f, vals, x.grad[ind], i, ind, check),
        )
