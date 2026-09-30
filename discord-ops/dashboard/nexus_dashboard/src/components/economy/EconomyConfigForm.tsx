"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import * as z from "zod";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { useEffect } from "react";

const formSchema = z.object({
  loot_multiplier: z.number().min(0.1).max(10),
  lifetime_multiplier: z.number().min(0.1).max(10),
  zombie_max: z.number().min(0).max(5000),
  animal_max: z.number().min(0).max(1000),
});

export function EconomyConfigForm() {
  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      loot_multiplier: 1.0,
      lifetime_multiplier: 1.0,
      zombie_max: 1000,
      animal_max: 200,
    },
  });

  useEffect(() => {
    // Load initial config
    fetch("/api/server/economy/config")
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load");
        return res.json();
      })
      .then((data) => {
        if (data.economy) {
          form.reset({
            loot_multiplier: data.economy.loot_multiplier ?? 1.0,
            lifetime_multiplier: data.economy.lifetime_multiplier ?? 1.0,
            zombie_max: data.economy.zombie_max ?? 1000,
            animal_max: data.economy.animal_max ?? 200,
          });
        }
      })
      .catch(() => toast.error("Could not load economy config"));
  }, [form]);

  async function onSubmit(values: z.infer<typeof formSchema>) {
    try {
      const res = await fetch("/api/server/economy/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.message || "Failed to update");
      }

      toast.success("Economy configuration updated and applied");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to update");
    }
  }

  return (
    <Form form={form} onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <FormField
          control={form.control}
          name="loot_multiplier"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Loot Multiplier</FormLabel>
              <FormControl>
                <Input type="number" step="0.1" {...field} />
              </FormControl>
              <FormDescription>
                Global multiplier for item nominal counts (e.g., 1.5 = 50% more loot).
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="lifetime_multiplier"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Lifetime Multiplier</FormLabel>
              <FormControl>
                <Input type="number" step="0.1" {...field} />
              </FormControl>
              <FormDescription>
                How long items stay on the ground (e.g., 0.5 = despawn twice as fast).
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="zombie_max"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Max Zombies</FormLabel>
              <FormControl>
                <Input type="number" {...field} />
              </FormControl>
              <FormDescription>
                Maximum global zombie count.
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="animal_max"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Max Animals</FormLabel>
              <FormControl>
                <Input type="number" {...field} />
              </FormControl>
              <FormDescription>
                Maximum global animal count.
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
      </div>
      <Button type="submit">Save & Apply Configuration</Button>
    </Form>
  );
}
export default EconomyConfigForm;

export { EconomyConfigForm };
