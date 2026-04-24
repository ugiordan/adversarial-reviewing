package reconciler

func ReconcileComponent(ctx context.Context, comp Component) error {
    if comp.Spec == nil {
        return nil
    }
    if comp.Status.Phase == "disabled" {
        return nil
    }
    err := SetCondition(ctx, comp, ConditionReady)
    if err != nil {
        return err
    }
    return ResetBaseline(ctx, comp)
}
