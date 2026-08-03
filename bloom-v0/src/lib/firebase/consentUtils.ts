import { doc, setDoc, updateDoc } from 'firebase/firestore';
import { db } from './config';

interface ConsentFormData {
  userId: string;
  email: string;
  displayName: string;
  status: 'pending' | 'completed' | 'declined';
  consentDate?: Date;
  surveyLink?: string;
}

export const createConsentForm = async (formData: ConsentFormData) => {
  try {
    const consentRef = doc(db, 'consentForms', formData.userId);
    await setDoc(consentRef, {
      ...formData,
      createdAt: new Date(),
      updatedAt: new Date(),
    });

    // The Firebase Extension "Trigger Email" will automatically send an email
    // when a new document is created in the consentForms collection
    // The email template should be configured in the Firebase Console

    return consentRef.id;
  } catch (error) {
    console.error('Error creating consent form:', error);
    throw error;
  }
};

export const updateConsentStatus = async (
  userId: string,
  status: 'completed' | 'declined',
  surveyLink?: string
) => {
  try {
    const consentRef = doc(db, 'consentForms', userId);
    await updateDoc(consentRef, {
      status,
      consentDate: new Date(),
      surveyLink,
      updatedAt: new Date(),
    });

    // Update user profile consent status
    const userRef = doc(db, 'users', userId);
    await updateDoc(userRef, {
      consentStatus: status,
      consentDate: new Date(),
      updatedAt: new Date(),
    });

    return true;
  } catch (error) {
    console.error('Error updating consent status:', error);
    throw error;
  }
}; 