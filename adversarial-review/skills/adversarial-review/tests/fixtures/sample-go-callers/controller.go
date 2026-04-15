package reconciler

func reconcileLoop(ctx context.Context, components []Component) error {
    for _, comp := range components {
        if err := ReconcileComponent(ctx, comp); err != nil {
            return err
        }
    }
    return nil
}

func processComponent(ctx context.Context, comp Component) error {
    if feature.IsEnabled(comp.Name) {
        return ReconcileComponent(ctx, comp)
    }
    return nil
}
