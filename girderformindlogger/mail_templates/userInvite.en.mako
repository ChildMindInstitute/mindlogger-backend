## -*- coding: utf-8 -*-
<%include file="_header.mako"/>

<div style="max-width: 440px;">
    <p>
        ${userName}
    </p>
    <p style="margin-top: 15px;">
        Welcome to ${appletName}!
    </p>

    <p>
        You have been invited to become a ${role} of "${appletName}", which runs in the MindLogger app (see below).
    </p>
    <p style="margin-top: 10px;">
        To accept this invitation, click below and your internet browser will open to the ${appletName} invitation page:
    </p>
    <p style="text-align: center;margin-top: 12px;">
        <a
            href="${url}/accept"
            style="padding: 0.4rem 1rem; font-size: 0.8rem; line-height: 1.5; border-radius: 0.3rem; margin: 4px; display: inline-block; font-weight: 400; text-align: center; vertical-align: middle; text-decoration: none; color: #ffffff; background-color: rgb(88, 217, 65); border-color: rgb(88, 217, 65);"
        >
            Go to "${appletName}" invitation page
        </a> 
    </p>
    <p style="margin-top: 6px;">
        After you have accepted the invitation, you will be able to access ${appletName} in the free MindLogger app on your mobile device, if you follow three simple steps (see the <a href="https://mindlogger.org//guides/user-guide.html" target="_blank">user guide</a> for greater detail):
    </p>
    <ol>
        <li>Install the MindLogger app on your mobile device, if it isn’t already installed.</li>
        <li>Open the MindLogger app on your mobile device, and log in 
            % if not newUser: 
                (if you have a MindLogger account) or sign up (if you are new to MindLogger). To sign up, tap “New User” on the login screen, and enter the email address where you received this email invitation. 
            % endif
        </li>
        <li>Tap "${appletName}" on the MindLogger home screen and you are ready to go!
            If "${appletName}" does not appear, refresh the screen by sliding your finger downwards from the top, and a spinning wheel should appear while loading "${appletName}".
        </li>
    </ol>
    <p style="margin-top: 10px;">
        Thank you for accepting the invitation to use ${appletName}! 
    <p/>

    <div style="border-top: 2px solid rgb(216,216,216); padding-top: 25px; ">
        <img
            src="https://cmi-logos.s3.amazonaws.com/ChildMindInstitute_Logo_Horizontal_RGB.png"
            style="width: 200px; margin-left: 20px;"
        >
    </div>
    <small>
        The Child Mind Institute is the creator of MindLogger, a platform for creating applets, but is not responsible for applet content created by outside parties.
    </small>
</div>

