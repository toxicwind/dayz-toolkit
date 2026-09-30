import { UserProfile } from '@clerk/nextjs';

export function ProfileViewPage() {
  return (
    <div className='flex w-full flex-col p-4 text-center border rounded-lg py-12'>
      <p className='text-muted-foreground'>Clerk User Profile is temporarily disabled.</p>
      {/* <UserProfile /> */}
    </div>

  );
}
export default ProfileViewPage;

export { ProfileViewPage };
