'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { toast } from 'sonner';

interface ParticipationModalProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  // Optional callback for after successful submission
  onSuccess?: () => void; 
}

// Simple email validation regex
const EMAIL_REGEX = /^\S+@\S+\.\S+$/;

export function ParticipationModal({ isOpen, onOpenChange, onSuccess }: ParticipationModalProps) {
  const [email, setEmail] = useState('');
  const [consent, setConsent] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const resetForm = () => {
      setEmail('');
      setConsent(false);
      setIsSubmitting(false);
  };

  const handleSubmit = async () => {
    if (!consent) {
      toast.error('Please provide consent to participate.');
      return;
    }
    if (!email || !EMAIL_REGEX.test(email)) {
      toast.error('Please enter a valid email address.');
      return;
    }

    setIsSubmitting(true);
    console.log("Submitting participation interest:", { email });

    // --- TODO: Replace with actual API call to backend email service --- 
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1500));
      // Assume success
      console.log("Simulated email sent successfully to backend for:", email);
      toast.success("Thank you for your interest! We will be in touch.");
      onOpenChange(false); // Close modal
      resetForm(); // Reset form state
      onSuccess?.(); // Trigger optional success callback (e.g., for download)
    } catch (error) {
      console.error("Participation submission failed:", error);
      toast.error("Submission failed. Please try again later.");
    } finally {
      setIsSubmitting(false);
    }
    // --------------------------------------------------------
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => {
        onOpenChange(open);
        if (!open) resetForm(); // Reset form if modal is closed externally
    }}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle className="text-lg font-semibold">Participate in Our Research</DialogTitle>
          <DialogDescription className="text-sm text-gray-600 pt-2">
            We are seeking dental educators to participate in our study on AI-assisted VR content creation. Your insights are valuable!
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="email-modal" className="text-right">Email</Label>
            <Input
              id="email-modal"
              type="email"
              placeholder="your.email@example.com"
              className="col-span-3"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={isSubmitting}
            />
          </div>
          <div className="flex items-center space-x-2 mt-2 pl-1">
            <Checkbox 
              id="consent-modal" 
              checked={consent} 
              onCheckedChange={(checked: boolean) => setConsent(checked)} 
              disabled={isSubmitting}
            />
            <Label htmlFor="consent-modal" className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
              I consent to be contacted for research participation.
            </Label>
          </div>
          <p className="text-xs text-gray-500 mt-1 pl-1">
            🔒 Your information will be treated confidentially according to research ethics guidelines.
          </p>
        </div>
        <DialogFooter>
          <Button
            type="submit"
            onClick={handleSubmit}
            disabled={isSubmitting || !consent || !email} // Disable if submitting or invalid
          >
            {isSubmitting ? "Submitting..." : "Submit Interest"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
} 